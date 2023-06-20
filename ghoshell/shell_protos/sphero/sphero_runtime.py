# from __future__ import annotations
#
# import struct
# import threading
# import time
# from threading import Thread
# from typing import Callable
# from typing import List
#
# from rich.console import Console
# from spherov2.commands.sensor import Sensor, CollisionDetected
#
#
# def __collision_detected_notify_helper(listener, packet):
#     """
#     解决 Spherov2 解码 bolt 的 bug?
#     """
#     unpacked = struct.unpack('>3hB3hBH', packet.data)
#     listener(CollisionDetected(acceleration_x=unpacked[0] / 4096, acceleration_y=unpacked[1] / 4096,
#                                acceleration_z=unpacked[2] / 4096, x_axis=bool(unpacked[3] & 1),
#                                y_axis=bool(unpacked[3] & 2), power_x=unpacked[4], power_y=unpacked[5],
#                                power_z=unpacked[6], speed=unpacked[7], time=unpacked[8] / 1000))
#
#
# Sensor.collision_detected_notify = (24, 18, 0xff), __collision_detected_notify_helper
#
# from spherov2 import scanner
# from spherov2.sphero_edu import SpheroEduAPI, EventType
# from spherov2.types import Color
#
# from ghoshell.prototypes.sphero import *
# from ghoshell.messages import Text
#
#
# class SpheroBoltKernel:
#     """
#     kernel
#     """
#
#     def __init__(
#             self,
#             api: SpheroEduAPI,
#             console: Console,
#             speaker_callback: Speaker,
#             collision_callback: OnCollision,
#     ):
#         self.speaker_callback = speaker_callback
#         self.collision_callback = collision_callback
#         self.api = api
#         self.console = console
#
#         # sphero 状态.
#         self._front_angle: int = 0
#
#         self.runtime_mode: bool = False
#         self.cmd: SpheroCommand | None = None
#         self.cmd_start_at: float = 0  # 命令开始的时间
#         self.cmd_ran_frames: int = 0  # 运行过的帧数
#         self.api.register_event(EventType.on_collision, self._on_collision)
#
#         self.stop_at_collision: bool = False
#
#     def _on_collision(self, api: SpheroEduAPI):
#         if self.stop_at_collision:
#             return
#         self.stop_at_collision = True
#         api.stop_roll()
#         api.set_front_led(Color(255, 0, 0))
#         self.console.print("on_collision")
#         if self.collision_callback is not None:
#             self.collision_callback()
#
#     def finish_cmd(self, now: float) -> str:
#         if self.cmd is None:
#             return ""
#         event_msg = self.cmd.on_stop(self.cmd_start_at, now)
#         self.reset_command()
#         return event_msg
#
#     def reset_command(self) -> None:
#         """
#         重置 sphero 状态.
#         """
#         self.cmd_start_at = 0
#         self.api.clear_matrix()
#         self.cmd = None
#         self.cmd_ran_frames = -1
#         self._front_angle = 0
#         self.api.stop_roll()
#         self.stop_at_collision = False
#
#     def set_command(self, cmd: SpheroCommand, runtime_mode: bool = False) -> None:
#         """
#         设置当前命令.
#         """
#         self.reset_command()
#         self.cmd = cmd
#         self.runtime_mode = runtime_mode
#
#     def run_frame(self, at: float) -> bool:
#         """
#         运行一帧.
#         """
#         cmd = self.cmd
#         if cmd is None:
#             return False
#         self.cmd_ran_frames += 1
#         if self.cmd_ran_frames == 0:
#             self.console.print("executing:", cmd.dict())
#
#         if isinstance(cmd, Roll):
#             return self._roll(cmd, at)
#         elif isinstance(cmd, Stop):
#             return self._stop(cmd, at)
#         elif isinstance(cmd, Say):
#             return self._say(cmd, at)
#         elif isinstance(cmd, Spin):
#             return self._spin(cmd, at)
#         else:
#             self.reset_command()
#             return False
#
#     def _roll(self, cmd: Roll, at: float) -> bool:
#         if self.cmd_start_at + cmd.duration < at:
#             self.api.stop_roll()
#             self.api.set_front_led(Color(0, 0, 0))
#             return False
#         if self.cmd_ran_frames == 0:
#             self.api.set_front_led(Color(0, 200, 0))
#             self.api.set_speed(cmd.speed)
#             heading = self._front_angle + cmd.heading % 360
#             self.api.set_heading(heading)
#         return True
#
#     def _stop(self, cmd: Stop, at: float) -> bool:
#         if self.cmd_ran_frames == 0:
#             self.api.set_front_led(Color(200, 0, 0))
#             self.api.set_back_led(Color(200, 0, 0))
#             self.api.stop_roll()
#         return False
#
#     def _say(self, cmd: Say, at: float) -> bool:
#         if self.cmd_ran_frames == 0:
#             self.api.set_main_led(Color(0, 0, 200))
#             self.speaker_callback(Text(content=cmd.text))
#         self.api.clear_matrix()
#         return False
#
#     def _spin(self, cmd: Spin, at: float) -> bool:
#         if self.cmd_ran_frames == 0:
#             self.api.set_front_led(Color(0, 200, 0))
#             self.api.spin(cmd.angle, cmd.duration)
#         if self.cmd_start_at + cmd.duration >= at:
#             return True
#         # 变更角度.
#         self._front_angle = self._front_angle + cmd.angle % 360
#         self.api.set_front_led(Color(0, 0, 0))
#         return False
#
#     def close(self) -> None:
#         self.reset_command()
#
#
# Speaker = Callable[[Text], None]
# Dispatcher = Callable[[SpheroEventMessage], None]
# OnCollision = Callable[[], None]
#
#
# class SpheroBoltRuntime:
#
#     def __init__(
#             self,
#             speak: Speaker,
#             dispatcher: Dispatcher,
#             console: Console,
#             frame: float = 1,
#     ):
#         self._speak = speak
#         self._console = console
#         self._dispatcher = dispatcher
#
#         self._frame = frame
#         self._last_frame: float = 0
#         self._cmd_stack_lock = threading.Lock()
#
#         # 运行时的协程.
#         self._thread = Thread(target=self._do_run)
#         self._running: bool = True
#
#         # kernel
#         self._kernel: SpheroBoltKernel | None = None
#         # 运行中的 sphero 命令消息.
#         self._cmds_message: SpheroCommandMessage | None = None
#         # command 的 stack
#         self._cmd_stack: List[SpheroCommand] = []
#         self._cmd_events: List[str] = []
#
#         self.ready = False
#         self.error: str | None = None
#
#     def close(self):
#         self._running = False
#         if self._kernel is not None:
#             self._kernel.close()
#         self._thread.join()
#
#     def _on_collision(self) -> None:
#         self.set_cmd_message(None)
#
#     def _do_run(self):
#         """
#         use thread to async run bolt
#         """
#         bolt = scanner.find_BOLT()
#         with SpheroEduAPI(bolt) as api:
#             # kernel 定义为一个简单状态机. 与命令无关.
#             kernel = SpheroBoltKernel(api, self._console, self._speak, self._on_collision)
#             self._kernel = kernel
#             self.ready = True
#
#             # 运行每一帧.
#             while self._running:
#                 now = time.time()
#                 try:
#                     cmd_is_running = kernel.run_frame(now)
#                 except Exception as e:
#                     self._console.print(e)
#                     self._sleep_frame()
#                     continue
#
#                 # 命令是否已经结束.
#                 if cmd_is_running:
#                     self._sleep_frame()
#                     continue
#                 else:
#                     # 结束一个指令的话, 要记录事件.
#                     # 这样实现一点也不好看, 归根到底是把 runtime 和 kernel 拆分了.
#                     # 应该把两者合并.
#                     e = self._kernel.finish_cmd("", now)
#                     if e:
#                         self._cmd_events.append(e)
#
#                 # 如果命令栈已经执行完毕.
#                 if len(self._cmd_stack) == 0:
#                     self.finish_cmd_stack("", True, now)
#                     self._sleep_frame()
#                     continue
#                 # 新的命令出栈.
#                 cmd = self._cmd_stack[0]
#                 self._cmd_stack = self._cmd_stack[1:]
#                 kernel.set_command(cmd, self._cmds_message.runtime_mode)
#             kernel.close()
#
#     def finish_cmd_stack(self, stopped: str, deliver_events: bool, now: float) -> None:
#         """
#         清空命令.
#         """
#         self._cmd_stack_lock.locked()
#         try:
#             if self._cmds_message is None:
#                 return
#             last_event = self._kernel.finish_cmd(now)
#             if last_event:
#                 self._cmd_events.append(last_event)
#
#             if deliver_events:
#                 # 是否需要立刻发送事件. 有三种情况会导致指令被中断:
#                 # 1. 指令全部完成. 需要发送事件.
#                 # 2. 得到了新的指令, 不需要发送事件.
#                 # 3. 指令因为碰撞事件被中断, 需要发送事件.
#                 self._deliver_runtime_events(stopped)
#             self._cmd_stack = []
#             self._cmds_message = None
#         finally:
#             self._cmd_stack_lock.release()
#
#     def _deliver_runtime_events(self, stopped: str) -> None:
#         """
#         按需发送运行时消息给服务端.
#         """
#         # 只有运行中命令存在的时候, 才存在发送事件的需要.
#         if self._cmds_message is None or not self._cmds_message.runtime_mode:
#             return
#
#         events = self._cmd_events
#         self._cmd_events = []
#         if events:
#             message = SpheroEventMessage(direction=self._cmds_message.direction, events=events, stopped=stopped)
#             self._dispatcher(message)
#
#     def run(self):
#         """
#         正式运行命令.
#         """
#         self._thread.start()
#
#     def set_cmd_message(self, message: SpheroCommandMessage | None) -> None:
#         """
#         重置当前命令.
#         """
#         if self._cmds_message is not None:
#             # 重置命令导致的中断.
#             self.finish_cmd_stack("receive new commands", False, time.time())
#
#         if message is not None:
#             self._cmds_message = message
#             self._cmd_stack = message.to_commands()
#
#     def _sleep_frame(self) -> None:
#         now = time.time()
#         duration = self._last_frame + self._frame - now
#         if duration > 0:
#             # 没有过足够的时间, 才需要启动 sleep
#             time.sleep(duration)
#             now = time.time()
#         self._last_frame = now
