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
        """
        输出许多字符串.
        """
        content = "\n\n".join(lines)
        message = Text(
            content=content,
            markdown=markdown,
        )
        self.output(message)
        return self

    def markdown(self, text: str) -> "Sender":
        """
        纯语法糖.
        """
        return self.text(text, markdown=True)

    def json(self, value: Any, indent: int = 2) -> "Sender":
        """
        json 输出的语法糖.
        """
        string = json.dumps(value, indent=indent, ensure_ascii=False)
        return self.text(f"```json\n{string}\n```", markdown=True)

    def err(self, errmsg: str, code: int = ErrMessageException.CODE, at: str = "") -> "Sender":
        """
        输出错误消息的语法糖.
        """
        message = ErrMsg(errcode=code, errmsg=errmsg, at=at)
        return self.output(message)

    @abstractmethod
    def async_input(
            self,
            message: Message,
            process_id: str | None = None,
            trace: Optional["Trace"] = None,
            tid: str | None = None,
    ) -> "Sender":
        """
        发出一个异步消息给 Ghost.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
