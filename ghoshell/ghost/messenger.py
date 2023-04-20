from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ghoshell.messages import Message


class Messenger(metaclass=ABCMeta):
    """
    输出消息的工具类封装.
    主要用途: 提供各种语法糖.
    """

    @abstractmethod
    def output(self, *messages: "Message") -> "Messenger":
        pass

    @abstractmethod
    def async_input(self, message: "Message", pid: str) -> "Messenger":
        pass
