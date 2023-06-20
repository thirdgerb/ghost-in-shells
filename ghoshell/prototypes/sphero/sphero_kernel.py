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
from pydantic import BaseModel

Speaker = Callable[[str], None]
Console = Callable[[Any], None]
OnCollision = Callable[[], None]


class SpheroBoltStage(BaseModel, metaclass=ABCMeta):
    """
    Sphero 的某个运行状态.
    """
    # 命令实际开始运行时间.
    start_at: float = 0
    # 命令的实际运行帧数.
    ran_frames_count: int = -1
    # 命令的运行日志.
    runtime_log: str = ""

    @abstractmethod
    def plan_desc(self) -> str:
        """
        对运行计划的自然语言描述
        """
        pass

    def run_frame(self, kernel: SpheroKernel, at: float) -> bool:
        self.ran_frames_count += 1  # 第一次运行时, ran_frames_count == 0
        if self.ran_frames_count == 0:
            self.start_at = at
        is_running = self._run_frame(kernel, at)
        if not is_running:
            now = time.time()
            self.on_stop(now)
        return is_running

    @abstractmethod
    def _run_frame(self, kernel: SpheroKernel, at: float) -> bool:
        """
        运行本命令一帧.
        """
        pass

    def on_stop(self, stop_at: float) -> None:
        """
        结束时记录运行日志.
        """
        plan = self.plan_desc()
        duration = stop_at - self.start_at
        self.runtime_log = plan + f"实际执行 {duration} 秒."


class SpheroKernel:
    # 面朝角度.
    front_angle: int = 0
    # 待运行的栈. 右进左出.
    _stage_stacks: List[SpheroBoltStage] = []
    ran_stacks: List[SpheroBoltStage] = []

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

    def current_stage(self) -> SpheroBoltStage | None:
        if len(self._stage_stacks) > 0:
            return self._stage_stacks[0]
        return None

    def shift_stage(self, at: float) -> bool:
        """
        完成掉一个状态位.
        """
        if len(self._stage_stacks) > 0:
            current = self._stage_stacks[0]
            current.on_stop(at)
            self.ran_stacks.append(current)
            self._stage_stacks = self._stage_stacks[1:]
        return len(self._stage_stacks) > 0

    def insert_stages(self, stages: List[SpheroBoltStage]):
        """
        在现在的调用栈上插入.
        """
        for stage in self._stage_stacks:
            stages.append(stage)
        self._stage_stacks = stages

    def toward(self, heading: int) -> int:
        return round((self.front_angle + heading) % 360)

    def reset(self) -> None:
        self.api.stop_roll()
        self.api.clear_matrix()
        self.front_angle = 0
        self._stage_stacks = []
        self.ran_stacks = []
