from __future__ import annotations

import math
from abc import ABCMeta, abstractmethod
from typing import ClassVar, List, Dict, Type

from pydantic import Field
from spherov2.types import Color

from ghoshell.prototypes.sphero.sphero_kernel import SpheroKernel, SpheroBoltStage

xx = math.sin(30)


class SpheroCommand(SpheroBoltStage, metaclass=ABCMeta):
    """
    Sphero 指令的抽象. 用于 DSL
    """

    method: ClassVar[str] = ""

    @classmethod
    @abstractmethod
    def desc(cls) -> str:
        pass

    #         return """
    # 各种指令可能用到的参数:
    # * speed: int 类型, 定义我的速度, 范围是 -255 到 255, 负数表示向后滚动, 0 表示停止. 默认值是 100
    # * heading: int 类型, 定义我的方向, 范围是 -360 到 360, 对应圆形的角度. 默认值是 0
    # * duration: float 类型, 定义指令持续的时间, 单位是秒. 默认值是 0, 表示只执行一次. 为负数表示一直持续
    # * angle: int 类型, 表示一个旋转角度, 负数表示逆时针旋转, 正数表示顺时针旋转. 360 表示一个圆.
    # """

    @classmethod
    def read(cls, data: Dict) -> SpheroCommand | None:
        if data.get("method", "") == cls.method:
            return cls(**data)
        return None

    def to_command_data(self) -> Dict:
        data = self.dict()
        data["method"] = self.method
        return data


class Roll(SpheroCommand):
    """
    最基本的滚动命令.
    """

    method = "roll"
    heading: int = 0
    speed: int = 100
    duration: float = 1

    @classmethod
    def desc(cls) -> str:
        # todo: 看起来参数可以提前定义.
        return """
* roll: 控制我的身体滚动. 
  * speed: int 类型, 定义滚动的速度, 范围是 0 到 255, 0 表示停止. 默认值是 100
  * heading: int 类型, 定义滚动的方向, 范围是 -360 到 360, 对应圆形的角度. 正前方是 0, 正后方是 180, 向左是 270, 向右是 90. 
  * duration: float 类型, 定义滚动的时间, 单位是秒. 默认值是 1. 为负数表示一直持续
"""

    def plan_desc(self) -> str:
        return f"计划以{self.speed}的速度, {self.heading}的角度, 滚动{self.duration}秒."

    def _run_frame(self, kernel: SpheroKernel, at: float):
        if self.start_at + self.duration < at:
            kernel.api.stop_roll()
            kernel.api.set_front_led(Color(0, 0, 0))
            return False
        if self.ran_frames_count == 0:
            kernel.api.set_front_led(Color(0, 200, 0))
            kernel.api.set_speed(self.speed)
            heading = kernel.toward(self.heading)
            kernel.api.set_heading(heading)
        return True


class Spin(SpheroCommand):
    """
    旋转的命令, 需要变更朝向. 
    """
    method = "spin"

    angle: int = 90
    duration: float = 1

    @classmethod
    def desc(cls) -> str:
        return """
* spin: 原地转动
  * angle: int 类型. 是一个转动的角度, 会变更我的正面指向. 360 表示 360度, 是一个整圆. 注意, 会变更我面向的角度.  
  * duration: float 类型, 定义转动的时间. 默认值是 1. 单位是秒. 
"""

    def plan_desc(self) -> str:
        return f"计划在{self.duration}秒内, 旋转 {self.angle} 度."

    def _run_frame(self, kernel: SpheroKernel, at: float):
        if self.ran_frames_count == 0:
            kernel.api.set_front_led(Color(0, 200, 0))
            kernel.api.spin(self.angle, self.duration)
        if self.start_at + self.duration >= at:
            return True
        # 变更角度.
        kernel.front_angle = kernel.toward(self.angle)
        kernel.api.set_front_led(Color(0, 0, 0))
        return False


class Say(SpheroCommand):
    """
    说话
    """

    method = "say"
    text: str

    @classmethod
    def desc(cls) -> str:
        return """
* say: 用我的声音模块说话    
    * text: 要说的话的内容. 
"""

    def plan_desc(self) -> str:
        return f"计划对用户说: {self.text}"

    def _run_frame(self, kernel: SpheroKernel, at: float):
        if self.ran_frames_count == 0:
            kernel.api.set_main_led(Color(0, 0, 200))
            kernel.speak(self.text)
        kernel.api.clear_matrix()
        return False


class Stop(SpheroCommand):
    method = "stop"
    duration: int = 1

    @classmethod
    def desc(cls) -> str:
        return """
* stop: 强行停止转动. 
    * duration: 停止动作持续的时间, 默认是 1秒. 通常不需要改动. 
"""

    def plan_desc(self) -> str:
        return f"计划停止所有动作."

    def _run_frame(self, kernel: SpheroKernel, at: float):
        if self.ran_frames_count == 0:
            kernel.api.set_front_led(Color(200, 0, 0))
            kernel.api.set_back_led(Color(200, 0, 0))
            kernel.api.stop_roll()
        in_duration = self.start_at + self.duration > at
        if not in_duration:
            kernel.api.clear_matrix()
        return in_duration


class Loop(SpheroCommand):
    """
    循环执行命令.
    """

    method = "loop"
    direction: str  # 循环执行的命令描述
    times: int = 1  # 循环执行的次数.
    # 需要执行的 commands 命令.
    commands: List[Dict] = Field(default_factory=lambda: [])
    # 已经运行的次数.
    loop_count: int = 0

    @classmethod
    def desc(cls) -> str:
        return """
* loop: 循环执行一段指令
    * times: int 类型, 表示循环执行的次数. 
    * direction: str 类型, 用自然语言描述需要循环执行的命令. 比如 `画正方形`
"""

    def plan_desc(self) -> str:
        return f"计划循环执行命令 `{self.direction}` 共{self.times}次."

    def on_stop(self, stop_at: float) -> str:
        duration = stop_at - self.start_at
        return f"实际运行 {self.loop_count} 次, 在{duration}秒后停止."

    def _run_frame(self, kernel: SpheroKernel, at: float) -> bool:
        is_finished = self.loop_count >= self.times
        if is_finished:
            return False
        self.loop_count += 1
        stages = command_data_to_commands(self.commands)
        kernel.insert_stages(stages)
        return True


class RoundRoll(SpheroCommand):
    """
    以圆弧的形式滚动.
    """

    method = "round_roll"

    speed: int
    angle: int
    duration: float

    @classmethod
    def desc(cls) -> str:
        return """
* round_roll: 从当前位置出发, 会按照圆形的弧线进行滚动. 不适合用来走出直线. 
    * speed: int 类型, 范围是 0 ~ 255, 表示滚动的速度. 默认是 50. 
    * angle: int 类型, 负数表示逆时针旋转, 正数为顺时针旋转. 表示滚动时要经过的角度. 比如 360 表示会沿圆弧滚动回起点.
    * duration: float 类型, 单位是秒. 表示完成滚动的时间. 
"""

    def plan_desc(self) -> str:
        return f"计划以{self.speed} 的速度, 在 {self.duration} 秒内完成 {self.angle} 度的圆弧"

    def _run_frame(self, kernel: SpheroKernel, at: float) -> bool:
        in_duration = self.start_at + self.duration > at
        if not in_duration:
            kernel.api.stop_roll()
            kernel.api.set_front_led(Color(0, 0, 0))
            return False

        if self.ran_frames_count == 0:
            kernel.api.set_front_led(Color(0, 200, 0))

        passed = at - self.start_at
        angle = round(self.angle * passed / self.duration)
        heading = kernel.toward(angle)
        kernel.api.set_heading(heading)
        kernel.api.set_speed(self.speed)
        # 不改变朝向.
        return in_duration


class LambdaRoll(SpheroCommand):
    """
    高级命令形式, 可以用 python lambda 定义滚动时的速度与角度
    """

    method = "lambda_roll"

    speed: str  # 速度函数
    heading: str  # 方向函数
    duration: float  # 运行时间

    @classmethod
    def desc(cls) -> str:
        return """
* lambda_roll: 允许使用 python lambda 函数来定义滚动轨迹的方法. 可以使用 python 的 math 库. 对于直线轨迹不该用 lambda_roll, 还是 roll + spin 组合使用更合理.  
    * speed: str 类型, 接受一个 lambda 函数, 以 float 类型的 t 为参数 (表示经过时间, 单位是秒), 返回值是 int 类型, 表示速度, 范围是 -255 ~ 255. 例如 `lambda t: 100`, 表示速度恒定为 100
    * heading: str 类型, 接受一个 lambda 函数, 以 float 类型的 t 为参数 (表示经过时间, 单位是秒), 返回值是 int 类型, 表示角度. 例如 `lambda t: 10`, 表示滚动指向固定为 10. 注意 
"""

    def plan_desc(self) -> str:
        return f"计划在 {self.duration} 秒内, 以经过时间 t 为变量, 运行速度按函数 `{self.speed}`, 朝向按函数 `{self.heading}` 来滚动"

    def _run_frame(self, kernel: SpheroKernel, at: float) -> bool:
        in_duration = self.start_at + self.duration > at
        if not in_duration:
            kernel.api.stop_roll()
            kernel.api.set_front_led(Color(0, 0, 0))
            return False

        if self.ran_frames_count == 0:
            kernel.api.set_front_led(Color(0, 200, 0))
        t = at - self.start_at
        speed_fn = eval(self.speed)
        heading_fn = eval(self.heading)
        speed = speed_fn(t)
        heading = heading_fn(t)
        toward = kernel.toward(heading)
        kernel.api.set_heading(toward)
        kernel.api.set_speed(speed)
        return in_duration


class Ability(SpheroCommand):
    """
    使用一个已知的技能运动.
    """

    method = "ability_roll"

    name: str
    commands: List[Dict] = Field(default_factory=lambda: [])

    @classmethod
    def desc(cls) -> str:
        return """
* ability_roll: 使用一个已有的技能. 所谓技能, 是我已经掌握的一连串命令. 
    * name: str 类型, 表示技能的名字, 也是技能的 id.
"""


defined_commands: [Type[SpheroCommand]] = {cmd.method: cmd for cmd in [
    Roll,
    Spin,
    Stop,
    Say,
    Loop,
    # RoundRoll,
    LambdaRoll,
]}


def loop_check(command_data: Dict) -> Loop | None:
    return Loop.read(command_data)


def ability_check(command_data: Dict) -> Ability | None:
    return Ability.read(command_data)


def command_data_to_commands(commands: List[Dict]) -> List[SpheroCommand]:
    """
    将消息解析成一个个的命令对象.
    """
    result = []
    for message_data in commands:
        method = message_data.get("method", "")
        if method in defined_commands:
            wrapped = defined_commands[method].read(message_data)
            if wrapped is not None:
                result.append(wrapped)
    return result


def commands_instruction() -> str:
    """
    所有命令的描述的集合.
    """
    desc = []
    for key in sorted(defined_commands.keys()):
        cmd = defined_commands[key]
        desc.append(cmd.desc())
    return "\n".join(desc)
