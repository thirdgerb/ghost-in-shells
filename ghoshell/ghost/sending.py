from abc import ABCMeta, abstractmethod
from typing import Optional

from ghoshell.ghost.io import Message, Trace


class Sender(metaclass=ABCMeta):
    """
    输出消息的工具类封装.
    主要用途: 提供各种语法糖.
    """

    @abstractmethod
    def output(self, *messages: "Message", trace: Trace | None = None) -> "Sender":
        """
        输出一个消息.
        """
        pass

    @abstractmethod
    def async_input(
            self,
            message: Message,
            process_id: str | None = None,
            trace: Optional["Trace"] = None,
            tid: str | None = None,
    ) -> "Sender":
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
