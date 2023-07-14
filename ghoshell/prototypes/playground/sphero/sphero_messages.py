from __future__ import annotations

from typing import List, Dict

from ghoshell.messages import Message
from ghoshell.prototypes.playground.sphero.sphero_commands import SpheroCommand, defined_commands, Say


class SpheroEventMessage(Message):
    KIND = "sphero_event_message"

    direction: str
    # 运行状态的自然语言描述.
    runtime_logs: List[str]


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

    def say(self, content: str) -> None:
        self.commands.append(Say(content=content).to_command_data())

    def add(self, *command: SpheroCommand) -> None:
        for cmd in command:
            self.commands.append(cmd.to_command_data())

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
