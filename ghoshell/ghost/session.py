from abc import ABCMeta, abstractmethod
from typing import Dict


class Session(metaclass=ABCMeta):
    """
    Session 是 Clone 的会话存储.
    一个 Clone 可能同时处于多个 Session 中, Session 做的是事件流 (input/output) 的隔离.
    举个例子, 聊天机器人可能同时在 多个私聊/群聊 里:
    clone_id 确保它跨群共享记忆, 但 session 保证和 不同的人/不同的群 对话不会相互干扰
    """

    @property
    @abstractmethod
    def clone_id(self) -> str:
        """
        session 所处的 clone
        """
        pass

    @property
    @abstractmethod
    def session_id(self) -> str:
        """
        session 自身的 ID.
        """
        pass

    @abstractmethod
    def new_process_id(self) -> str:
        pass

    def current_process_id(self) -> str:
        pass

    @abstractmethod
    def new_message_id(self) -> str:
        pass

    @abstractmethod
    def set(self, key: str, value: Dict) -> bool:
        pass

    @abstractmethod
    def get(self, key: str) -> Dict | None:
        pass

    # todo: 先不急于实现
    # @abstractmethod
    # def save_input(self, _input: Input) -> None:
    #     pass
    #
    # @abstractmethod
    # def save_output(self, _output: Output) -> None:
    #     pass

    @abstractmethod
    def destroy(self) -> None:
        pass
