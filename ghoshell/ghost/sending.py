import json
from abc import ABCMeta, abstractmethod
from typing import Optional, Any

from ghoshell.ghost.exceptions import ErrMessageException
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

    def json(self, value: Any, indent: int = 2) -> "Sender":
        string = json.dumps(value, indent=indent)
        return self.text(f"```json\n{string}\n```", markdown=True)

    def err(self, line: str, code: int = ErrMessageException.CODE, at: str = "") -> "Sender":
        message = Error(errcode=code, errmsg=line, at=at)
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
