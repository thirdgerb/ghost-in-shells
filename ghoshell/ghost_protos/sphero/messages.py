from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import ClassVar, List, Dict, Type

from pydantic import BaseModel

from ghoshell.messages import Message


class SpheroCommand(BaseModel, metaclass=ABCMeta):
    """
    Sphero 指令的抽象. 用于 DSL
    """

    method: ClassVar[str] = ""

    @classmethod
    @abstractmethod
    def desc(cls) -> str:
        return """
各种指令可能用到的参数:
* speed: int 类型, 定义我的速度, 范围是 -255 到 255, 负数表示向后滚动, 0 表示停止. 默认值是 100
* heading: int 类型, 定义我的方向, 范围是 -360 到 360, 对应圆形的角度. 默认值是 0
* duration: float 类型, 定义指令持续的时间, 单位是秒. 默认值是 0, 表示只执行一次. 为负数表示一直持续
* angle: int 类型, 表示一个旋转角度, 负数表示逆时针旋转, 正数表示顺时针旋转. 360 表示一个圆. 
"""

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

    KIND = "sphero_commands"
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


class Roll(SpheroCommand):
    method = "roll"
    heading: int = 0
    speed: int = 100
    duration: float = 1

    @classmethod
    def desc(cls) -> str:
        # todo: 看起来参数可以提前定义.
        return """
* roll: 控制我的身体滚动. 
  * speed: int 类型, 定义滚动的速度, 范围是 -255 到 255, 负数表示向后滚动, 0 表示停止. 默认值是 100
  * heading: int 类型, 定义滚动的方向, 范围是 -360 到 360, 对应圆形的角度. 默认值是 0. 注意, 这里不会变更我的正面指向. 
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
  * angle: int 类型. 是一个转动的角度, 会变更我的正面指向. 360 表示 360度, 是一个整圆. 
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
