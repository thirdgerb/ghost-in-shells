from abc import ABCMeta, abstractmethod

from ghoshell.ghost.io import Input, Output


class Session(metaclass=ABCMeta):
    """
    Session 是 Clone 的会话存储.
    一个 Clone 可能同时处于多个 Session 中, Session 做的是事件流 (input/output) 的隔离.
    举个例子, 聊天机器人可能同时在 多个私聊/群聊 里:
    clone_id 确保它跨群共享记忆, 但 session 保证和 不同的人/不同的群 对话不会相互干扰
    """

    @abstractmethod
    def session_id(self) -> str:
        """
        session 的 id
        """
        pass

    @abstractmethod
    def save_input(self, _input: Input) -> None:
        pass

    @abstractmethod
    def save_output(self, _output: Output) -> None:
        pass
