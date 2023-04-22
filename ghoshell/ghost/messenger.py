from abc import ABCMeta, abstractmethod

from ghoshell.ghost.io import Message, Trace


class Messenger(metaclass=ABCMeta):
    """
    输出消息的工具类封装.
    主要用途: 提供各种语法糖.
    """

    @abstractmethod
    def output(self, *messages: "Message", trace: Trace | None = None) -> "Messenger":
        """
        输出一个消息.
        """
        pass

    @abstractmethod
    def async_input(self, message: "Message", pid: str) -> "Messenger":
        pass
