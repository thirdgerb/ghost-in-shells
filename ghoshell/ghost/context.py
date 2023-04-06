from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ghoshell.ghost.ghost import Clone
    from ghoshell.ghost.mindset import Thought
    from ghoshell.ghost.io import Input, Output, Message
    from ghoshell.ghost.operator import OperationManager


class Context(metaclass=ABCMeta):
    """
    Ghost 运行时的上下文, 努力包含一切核心逻辑与模块
    """

    @property
    @abstractmethod
    def clone(self) -> "Clone":
        pass

    def manage(self, this: "Thought") -> "OperationManager":
        return self.clone.manage(this)

    @property
    @abstractmethod
    def input(self) -> "Input":
        """
        请求的输入消息, 任何时候都不应该变更.
        """
        pass

    @abstractmethod
    def async_input(self, _input: "Input") -> None:
        """
        ghost 给 ghost 发送信息时使用
        """
        pass

    @abstractmethod
    def output(self, *actions: "Message") -> None:
        """
        输出各种动作, 实际上输出到 output 里, 给 shell 去处理
        """
        pass

    @abstractmethod
    def reset_input(self, _input: "Input") -> None:
        """
        重置上下文的 Input
        """
        pass

    @abstractmethod
    def gen_output(self) -> "Output":
        """
        将所有的输出动作组合起来, 输出为 Output
        所有 act 会积累新的 action 到 output
        它应该是幂等的, 可以多次输出.
        """
        pass

    @abstractmethod
    def reset_output(self, output: "Output") -> None:
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        上下文级别的缓存机制, 用在内存中.
        """
        pass

    def get(self, key: str) -> Optional[Any]:
        """
        从上下文中获取缓存. 工具机制.
        可惜没有泛型, python 很麻烦的.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        上下文运行完成后, 需要考虑 python 的特点, 要主动清理记忆
        """
        pass
