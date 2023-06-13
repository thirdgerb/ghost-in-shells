from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import ClassVar, List, Dict, Type

from pydantic import BaseModel, Field

from ghoshell.messages import Message


class SpheroCommand(BaseModel, metaclass=ABCMeta):
    """
    Sphero 指令的抽象. 用于 DSL
    """

    method: ClassVar[str] = ""

    event: str | None = None  # 是否是事件时触发.

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
            del data["method"]
            return cls(**data)
        return None

    # @abstractmethod
    # def call(
    #         self,
    #         kernel: SpheroBoltKernel,
    #         duration: float,
    #         count: int,
    # ) -> bool:  # 是否继续
    #     pass


class SpheroCommandMessage(Message):
    """
    用于 Shell 和 Ghost 通信用的指令.
    """

    KIND = "sphero_commands_message"
    direction: str = ""  # 对命令的基本描述
    runtime_mode: bool = False  # 是否是 runtime 模式. 如果是 runtime 模式, 运行时遇到事件或者命令执行完毕, 都会返回消息给 ghost
    commands: List[Dict] = []

    @classmethod
    def new(cls, *command: SpheroCommand) -> SpheroCommandMessage:
        result = cls()
        result.add(*command)
        return result

    def add(self, *command: SpheroCommand) -> None:
        for cmd in command:
            data = cmd.dict()
            data['method'] = cmd.method
            self.commands.append(data)

    @classmethod
    def wrap(cls, command_list: List[SpheroCommand]) -> SpheroCommandMessage:
        """
        使用 Message 合并指令.
        """
        result = cls()
        for cmd in command_list:
            result.add(cmd)
        return result

    def to_commands(self) -> List[SpheroCommand]:
        return command_message_to_commands(self)


class SpheroRuntimeMessage(Message):
    """
    sphero 运行时的上下文
    """

    KIND = "sphero_runtime_message"

    direction: str  # 运行命令的描述
    history: List[str] = Field(default_factory=lambda: [])  # 运行时的完整记录. 用自然语言描述.


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
    #
    # def call(
    #         self,
    #         kernel: SpheroBoltKernel,
    #         duration: float,
    #         count: int,
    # ) -> bool:
    #     if count == 0:
    #         kernel.api.set_heading(self.heading)
    #         kernel.api.set_speed(self.speed)
    #     if self.duration < 0:
    #         return True
    #     if duration >= self.duration:
    #         kernel.api.stop_roll()
    #         return False
    #     return False


class Spin(SpheroCommand):
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
    #
    # def call(
    #         self,
    #         kernel: SpheroBoltKernel,
    #         duration: float,
    #         count: int
    # ) -> bool:
    #     if count == 0:
    #         kernel.api.spin(self.angle, self.duration)
    #     return duration < self.duration
    #


class Say(SpheroCommand):
    method = "say"
    text: str

    @classmethod
    def desc(cls) -> str:
        return """
* say: 用我的声音模块说话    
    * text: 要说的话的内容. 
"""

    # def call(self, kernel: SpheroBoltKernel, duration: float, count: int) -> bool:
    #     if count == 0:
    #         kernel.speaker(self.text)
    #     return False


class Stop(SpheroCommand):
    method = "stop"
    duration: float = 0
    heading: int = 0

    @classmethod
    def desc(cls) -> str:
        return """
* stop: 强行停止转动. 
  * heading: 停止转动后, 面朝的方向. 范围是 0 ~ 360, 默认值是 0. 会变更正面指向. 
  * duration:  float 类型, 定义转动的时间. 默认值是 1. 为负数表示一直持续. 
"""


class Loop(SpheroCommand):
    """
    循环执行命令.
    """

    method = "loop"
    direction: str  # 循环执行的命令描述
    times: int = 1  # 循环执行的次数.
    # 需要执行的 commands 命令.
    commands: List[Dict] = Field(default_factory=lambda: [])

    @classmethod
    def desc(cls) -> str:
        return """
* loop: 循环执行一段指令
    * times: int 类型, 表示循环执行的次数. 
    * direction: string 类型, 用自然语言的方式来描述需要循环执行的命令是什么. 
"""


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
* round_roll: 从当前位置出发, 以圆弧的曲线进行滚动. 
    * speed: int 类型, 范围是 0 ~ 255, 表示滚动的速度. 
    * angle: int 类型, 负数表示逆时针旋转, 正数为顺时针旋转. 表示滚动时要经过的角度. 比如 360 表示会沿圆弧滚动回起点.
    * duration: float 类型, 单位是秒. 表示完成滚动的时间. 
"""


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
* lambda_roll: 允许使用 python lambda 函数来定义滚动轨迹的方法
    * speed: str 类型, 接受一个 lambda 函数, 以 float 类型的 t 为参数 (表示经过时间, 单位是秒), 返回值是 int 类型, 表示速度, 范围是 -255 ~ 255. 例如 `lambda t: 100`, 表示速度恒定为 100
    * heading: str 类型, 接受一个 lambda 函数, 以 float 类型的 t 为参数 (表示经过时间, 单位是秒), 返回值是 int 类型, 表示角度. 例如 `lambda t: 10`, 表示滚动指向固定为 10 
"""


class AbilityRoll(SpheroCommand):
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


class OnCollision(SpheroCommand):
    """
    等待服务端指令.
    """
    method = "on_collision"
    direction: str
    reset: bool
    commands: List[Dict] = Field(default_factory=lambda: [])

    event = "on_collision"

    @classmethod
    def desc(cls) -> str:
        return """
* on_collision: 发生碰撞事件时, 需要执行的命令. 默认是会中断当前命令, 然后继续运行.  
    * reset: bool 类型, 表示如果碰撞发生时, 是否要重置我运行中的所有命令. 
    * direction: string 类型, 发生碰撞时我要执行的命令, 用自然语言进行描述. 
"""


defined_commands: [Type[SpheroCommand]] = {cmd.method: cmd for cmd in [
    Roll,
    Spin,
    Stop,
    Say,
]}


def command_message_to_commands(message: SpheroCommandMessage) -> List[SpheroCommand]:
    """
    将消息解析成一个个的命令对象.
    """
    result = []
    for message_data in message.commands:
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
