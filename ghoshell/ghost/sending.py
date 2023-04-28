from abc import ABCMeta, abstractmethod
from typing import Optional

from ghoshell.ghost.exceptions import RuntimeException
from ghoshell.messages import *


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

    def text(self, *lines: str, markdown: bool = False) -> "Sender":
        content = "\n\n".join(lines)
        message = Text(
            content=content,
            markdown=markdown,
        )
        self.output(message)
        return self

    def err(self, line: str, code: int = RuntimeException.CODE) -> "Sender":
        message = Error(errcode=code, errmsg=line)
        return self.output(message)

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
