from __future__ import annotations

import time
from threading import Thread
from typing import Callable
from typing import List

from rich.console import Console
from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI, EventType
from spherov2.types import Color

from ghoshell.ghost_protos.sphero import *
from ghoshell.messages import Text


class SpheroBoltKernel:
    """
    kernel
    """

    def __init__(
            self,
            api: SpheroEduAPI,
            console: Console,
            speaker: Callable[[Text], None],
    ):
        self.speaker = speaker
        self.api = api
        self.console = console
        self.front_angle = 0
        self.cmd: SpheroCommand | None = None
        self.cmd_start_at: float = 0
        self.cmd_ran: int = 0
        self.api.register_event(EventType.on_collision, self._on_collision)

    def _on_collision(self, api: SpheroEduAPI):
        api.stop_roll()
        api.set_front_led(Color(255, 0, 0))
        self.console.print("")

    def reset_command(self) -> None:
        self.cmd_start_at = 0
        self.cmd = None
        self.cmd_ran = -1
        self.front_angle = 0
        self.api.stop_roll()

    def set_command(self, cmd: SpheroCommand) -> None:
        self.cmd_start_at = time.time()
        self.cmd = cmd
        self.cmd_ran = -1
        self.api.stop_roll()

    def run(self, at: float) -> bool:
        cmd = self.cmd
        if cmd is None:
            return False
        self.cmd_ran += 1
        if self.cmd_ran == 0:
            self.console.print("executing:", cmd.dict())

        if isinstance(cmd, Roll):
            return self._roll(cmd, at)
        elif isinstance(cmd, Stop):
            return self._stop(cmd, at)
        elif isinstance(cmd, Say):
            return self._say(cmd, at)
        elif isinstance(cmd, Spin):
            return self._spin(cmd, at)
        else:
            self.reset_command()

    def _roll(self, cmd: Roll, at: float) -> bool:
        if self.cmd_start_at + cmd.duration < at:
            self.api.stop_roll()
            self.api.set_front_led(Color(0, 0, 0))
            return False
        if self.cmd_ran == 0:
            self.api.set_speed(cmd.speed)
            self.api.set_front_led(Color(0, 200, 0))
            heading = self.front_angle + cmd.heading % 360
            self.api.set_heading(heading)
        return True

    def _stop(self, cmd: Stop, at: float) -> bool:
        if self.cmd_ran == 0:
            self.api.stop_roll(cmd.heading)
            self.front_angle = self.front_angle + cmd.heading % 360
            self.api.set_front_led(Color(200, 0, 0))
            self.api.set_back_led(Color(200, 0, 0))
        continual = self.cmd_start_at + cmd.duration >= at
        if not continual:
            self.api.set_front_led(Color(0, 0, 0))
            self.api.set_back_led(Color(0, 0, 0))
        return continual

    def _say(self, cmd: Say, at: float) -> bool:
        if self.cmd_ran == 0:
            self.api.set_main_led(Color(0, 0, 200))
            self.speaker(Text(content=cmd.text))
        self.api.clear_matrix()
        return False

    def _spin(self, cmd: Spin, at: float) -> bool:
        if self.cmd_ran == 0:
            self.api.spin(cmd.angle, cmd.duration)
            self.api.set_front_led(Color(0, 200, 0))
        if self.cmd_start_at + cmd.duration >= at:
            return True
        # 变更角度.
        self.front_angle = self.front_angle + cmd.angle % 360
        self.api.set_front_led(Color(0, 0, 0))
        return False

    def close(self) -> None:
        pass


class SpheroBoltRuntime:

    def __init__(
            self,
            speak: Callable[[Text], None],
            console: Console,
            frame: float = 1,
    ):
        self._speak = speak
        self._console = console

        self._frame = frame
        self._last_frame: float = 0

        self._cmds: List[SpheroCommand] = []
        self._thread = Thread(target=self._do_run)
        self._running: bool = True

        self.ready = False

    def close(self):
        self._running = False

    def _do_run(self):
        """
        """
        bolt = scanner.find_BOLT()
        with SpheroEduAPI(bolt) as api:
            kernel = SpheroBoltKernel(api, self._console, self._speak)
            self.ready = True
            while self._running:
                now = time.time()

                try:
                    more = kernel.run(now)
                except Exception as e:
                    self._console.print(e)
                    self._sleep_frame()
                    continue

                if more:
                    self._sleep_frame()
                    continue
                if len(self._cmds) == 0:
                    self._sleep_frame()
                    continue
                cmd = self._cmds[0]
                self._cmds = self._cmds[1:]
                kernel.set_command(cmd)

            kernel.close()

    def run(self):
        """
        正式运行命令.
        """
        self._thread.start()

    def set_cmd_message(self, message: SpheroCommandMessage) -> None:
        """
        重置当前命令.
        """
        self._cmds = message.to_commands()

    def _sleep_frame(self) -> None:
        now = time.time()
        duration = self._last_frame + self._frame - now
        if duration > 0:
            # 没有过足够的时间, 才需要启动 sleep
            time.sleep(duration)
            now = time.time()
        self._last_frame = now
