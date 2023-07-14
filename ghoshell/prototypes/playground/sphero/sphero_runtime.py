import threading
import time
from typing import Callable

from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI

from ghoshell.prototypes.playground.sphero.sphero_kernel import SpheroKernel, Speaker, Console, SpheroCmdStatus
from ghoshell.prototypes.playground.sphero.sphero_messages import SpheroCommandMessage, SpheroEventMessage, \
    command_message_to_commands

Dispatcher = Callable[[SpheroEventMessage], None]


class SpheroBoltRuntime:
    """
    sphero bolt 运行时, 主要解决与 ghost / shell 的交互问题.
    """

    def __init__(
            self,
            speak: Speaker,
            dispatcher: Dispatcher,
            console: Console,
            frame: float = 1,
    ):
        self._speak = speak
        self._console = console
        self._dispatch = dispatcher

        self._frame = frame
        self._last_frame: float = 0

        # 运行时的协程.
        self._thread = threading.Thread(target=self._do_run)
        self._running: bool = True

        # kernel
        self._kernel: SpheroKernel | None = None
        # 运行中的 sphero 命令消息.
        self._cmds_message: SpheroCommandMessage | None = None

        self.ready = False
        self.error: str | None = None

    def close(self):
        if self._running:
            self._running = False
            self._thread.join()

    def _on_collision(self) -> None:
        self.finish_cmd_stack(self._kernel, "碰到东西", deliver_events=True, now=time.time())
        self.set_cmd_message(None)

    def _do_run(self):
        """
        use thread to async run bolt
        """
        try:
            bolt = scanner.find_BOLT()
        except Exception as e:
            self.error = str(e)
            self.close()
            return

        with SpheroEduAPI(bolt) as api:
            # kernel 定义为一个简单状态机. 与命令无关.
            kernel = SpheroKernel(api, self._console, self._speak, self._on_collision)
            kernel.on_ready()

            self._kernel = kernel
            self.ready = True

            # 运行每一帧.
            while self._running:
                now = time.time()
                stage = kernel.current_stage()
                if stage is None:
                    self._sleep_frame()
                    continue
                cmd_is_running = stage.run_frame(kernel, now)

                # 命令是否已经结束.
                if not cmd_is_running:
                    stage.on_stop(now, "")
                    # 结束一个指令的话
                    more = kernel.shift_stage(now, "")
                    if not more:
                        self.finish_cmd_stack(kernel, "", True, now)
                self._sleep_frame()
        self.close()

    def finish_cmd_stack(self, kernel: SpheroKernel, stopped: str, deliver_events: bool, now: float) -> None:
        """
        清空命令.
        """
        kernel.stop_all()
        # kernel.shift_stage()
        if deliver_events:
            # 是否需要立刻发送事件. 有三种情况会导致指令被中断:
            # 1. 指令全部完成. 需要发送事件.
            # 2. 得到了新的指令, 不需要发送事件.
            # 3. 指令因为碰撞事件被中断, 需要发送事件.
            kernel.shift_stage(now, stopped)
            self._deliver_runtime_events(kernel)
        self._cmds_message = None

    def _deliver_runtime_events(self, kernel: SpheroKernel) -> None:
        """
        按需发送运行时消息给服务端.
        """
        # 只有运行中命令存在的时候, 才存在发送事件的需要.
        if self._cmds_message is None or not self._cmds_message.runtime_mode:
            return
        runtime_logs = []
        for ran in kernel.ran_stacks:
            log = ran.runtime_log
            if log:
                runtime_logs.append(log)
        direction = self._cmds_message.direction
        kernel.reset()
        if runtime_logs:
            message = SpheroEventMessage(
                direction=direction,
                runtime_logs=runtime_logs,
            )
            self._dispatch(message)

    def run(self):
        """
        正式运行命令.
        """
        self._thread.start()

    def set_cmd_message(self, message: SpheroCommandMessage | None) -> None:
        """
        重置当前命令.
        """
        if self._kernel is None:
            raise RuntimeError("kernel not prepared yet")

        # 结束上一个指令.
        if self._cmds_message is not None:
            # 重置命令导致的中断.
            self.finish_cmd_stack(self._kernel, "receive new commands", False, time.time())

        self._kernel.reset()
        if message is not None:
            self._cmds_message = message
            cmds = command_message_to_commands(message)
            stages = [SpheroCmdStatus(cmd) for cmd in cmds]
            self._kernel.insert_stages(stages)

    def _sleep_frame(self) -> None:
        now = time.time()
        duration = self._last_frame + self._frame - now
        if duration > 0:
            # 没有过足够的时间, 才需要启动 sleep
            time.sleep(duration)
            now = time.time()
        self._last_frame = now
