from __future__ import annotations

import struct
import time
from abc import ABCMeta, abstractmethod
from typing import Callable, List, Any

from spherov2.commands.sensor import Sensor, CollisionDetected


def __collision_detected_notify_helper(listener, packet):
    """
    解决 Spherov2 解码 bolt 的 bug?
    """
    unpacked = struct.unpack('>3hB3hBH', packet.data)
    listener(CollisionDetected(acceleration_x=unpacked[0] / 4096, acceleration_y=unpacked[1] / 4096,
                               acceleration_z=unpacked[2] / 4096, x_axis=bool(unpacked[3] & 1),
                               y_axis=bool(unpacked[3] & 2), power_x=unpacked[4], power_y=unpacked[5],
                               power_z=unpacked[6], speed=unpacked[7], time=unpacked[8] / 1000))


Sensor.collision_detected_notify = (24, 18, 0xff), __collision_detected_notify_helper

from spherov2.sphero_edu import SpheroEduAPI, EventType
from spherov2.types import Color

Speaker = Callable[[str], None]
Console = Callable[[Any], None]
OnCollision = Callable[[], None]


class SpheroRunnable(metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        pass

    @abstractmethod
    def runtime_plan(self) -> str:
        """
        对运行计划的自然语言描述
        """
        pass

    @abstractmethod
    def on_stop(self, duration: float, interrupt: str) -> str:
        pass

    @abstractmethod
    def run_frame(self, kernel: SpheroKernel, status: SpheroCmdStatus, at: float) -> bool:
        """
        运行本命令一帧.
        """
        pass

    def runtime_info(self, duration: float, interrupt: str) -> str:
        """
        对运行计划的自然语言描述
        """
        plan = self.runtime_plan()
        stop = self.on_stop(duration, interrupt)
        return f"\n* 目标: {plan}" \
               f"\n* 结果: {stop}"


class SpheroCmdStatus:
    """
    Sphero 的某个运行状态.
    """

    def __init__(self, runnable: SpheroRunnable, logging: bool = True):
        self._runnable = runnable
        # 命令实际开始运行时间.
        self.start_at: float = 0
        # 命令的实际运行帧数.
        self.ran_frames_count: int = -1
        # 命令的运行日志.
        self.runtime_log: str = ""
        self.loop_count: int = 0
        self.logging: bool = logging
        self.stopped: bool = False

    def run_frame(self, kernel: SpheroKernel, at: float) -> bool:
        if self.stopped:
            return False

        if self.start_at == 0:
            self.start_at = time.time()

        self.ran_frames_count += 1
        is_running = self._runnable.run_frame(kernel, self, at)
        return is_running

    def on_stop(self, stop_at: float, interrupt: str) -> None:
        """
        结束时记录运行日志.
        """
        if self.stopped:
            return
        self.stopped = True
        if self.start_at == 0:
            duration = 0
        else:
            duration = stop_at - self.start_at

        duration = round(duration, 2)
        log_str = self._runnable.runtime_info(duration, interrupt)
        if self.logging:
            self.runtime_log = self._runnable.name() + "|" + log_str


class SpheroKernel:
    # 面朝角度.
    front_angle: int = 0
    # 待运行的栈. 右进左出.
    stage_stacks: List[SpheroCmdStatus] = []
    ran_stacks: List[SpheroCmdStatus] = []

    def __init__(
            self,
            api: SpheroEduAPI,
            console: Console,
            speaker_callback: Speaker,
            collision_callback: OnCollision,
    ):
        self.speak = speaker_callback
        self.console = console
        self.api = api
        self._collision_callback = collision_callback
        self.stop_at_collision: bool = False
        self.api.register_event(EventType.on_collision, self._on_collision)

    def on_ready(self):
        self.api.set_front_led(Color(0, 50, 0))
        time.sleep(1)
        self.api.set_front_led(Color(0, 0, 0))

    def _on_collision(self, api: SpheroEduAPI) -> None:
        if self.stop_at_collision:
            return
        self.stop_at_collision = True
        api.stop_roll()
        api.set_front_led(Color(255, 0, 0))
        self.console("on_collision")
        if self._collision_callback is not None:
            self._collision_callback()
        api.set_front_led(Color(0, 0, 0))
        self.stop_at_collision = False

    def stop_all(self):
        self.api.stop_roll()
        self.api.clear_matrix()
        self.api.set_front_led(Color(0, 0, 0))
        self.api.set_back_led(Color(0, 0, 0))

    def current_stage(self) -> SpheroCmdStatus | None:
        if len(self.stage_stacks) > 0:
            return self.stage_stacks[0]
        return None

    def shift_stage(self, at: float, interrupt: str) -> bool:
        """
        完成掉一个状态位.
        """
        if len(self.stage_stacks) > 0:
            current = self.stage_stacks[0]
            current.on_stop(at, interrupt)
            self.ran_stacks.append(current)
            self.stage_stacks = self.stage_stacks[1:]
        return len(self.stage_stacks) > 0

    def insert_stages(self, stages: List[SpheroCmdStatus]):
        """
        在现在的调用栈上插入.
        """
        for stage in self.stage_stacks:
            stages.append(stage)
        self.stage_stacks = stages

    def toward(self, heading: int) -> int:
        # return heading
        return round((self.front_angle + heading) % 360)

    def reset(self) -> None:
        self.api.stop_roll()
        self.api.clear_matrix()
        self.stage_stacks = []
        self.ran_stacks = []
