from __future__ import annotations

from abc import ABCMeta, abstractmethod
from logging import LoggerAdapter
from typing import Any, Optional, TYPE_CHECKING, List, TypeVar, Type

from ghoshell.messages import Message

if TYPE_CHECKING:
    from ghoshell.container import Container
    from ghoshell.ghost.ghost import Clone
    from ghoshell.ghost.mindset import Thought, Mind
    from ghoshell.ghost.io import Input, Output, Trace
    from ghoshell.ghost.messenger import Messenger

M = TypeVar('M', bound=Message)


class Context(metaclass=ABCMeta):
    """
    Ghost 运行时的上下文, 努力包含一切核心逻辑与模块
    """

    @property
    @abstractmethod
    def clone(self) -> "Clone":
        pass

    def container(self) -> "Container":
        """
        容器层层传递.
        """
        return self.clone.container

    @abstractmethod
    def mind(self, this: "Thought") -> "Mind":
        """
        操作上下文的关键方法.
        """
        pass

    @abstractmethod
    def read(self, expect: Type[M]) -> M | None:
        """
        从上下文中读取信息.
        """
        pass

    @abstractmethod
    def send(self, _with: "Thought") -> Messenger:
        """
        以 Thought 为基础, 发出各种消息体给 Shell
        再由 Shell 发送出去.
        返回的 Messenger 是语法糖.
        """
        pass

    @property
    @abstractmethod
    def input(self) -> "Input":
        """
        请求的输入消息, 不应该被外部行为变更.
        要处理好指针的问题.
        但是 python 的话, 怎么样都不好解决深拷贝问题.
        考虑 Input 是 pydantic.BaseModel, 可以保存协议数据.
        """
        pass

    @abstractmethod
    def set_input(self, _input: "Input") -> None:
        """
        通过 set_input 可以强行变更当前上下文.
        """
        pass

    @abstractmethod
    def logger(self) -> LoggerAdapter:
        pass

    @abstractmethod
    def async_input(self, message: Message, pid: Optional[str] = None, trace: Optional["Trace"] = None) -> None:
        """
        ghost 给 ghost 发送信息时使用
        """
        pass

    @abstractmethod
    def output(self, _output: "Output") -> None:
        """
        输出各种动作, 实际上输出到 output 里, 给 shell 去处理
        """
        pass

    @abstractmethod
    def get_outputs(self) -> List["Output"]:
        """
        将所有的输出动作组合起来, 输出为 Output
        所有 act 会积累新的 action 到 output
        它应该是幂等的, 可以多次输出.
        """
        pass

    @abstractmethod
    def get_async_inputs(self) -> List["Input"]:
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        上下文级别的缓存机制, 用在内存中.
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        从上下文中获取缓存. 工具机制.
        可惜没有泛型, python 很麻烦的.
        """
        pass

    @abstractmethod
    def finish(self, failed: bool = False) -> None:
        """
        上下文运行完成后,
        需要考虑 python 的特点, 要主动清理记忆
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        运行结束后, 手动清理所有持有的对象.
        这个是为了解决脚本语言 GC 困难而强行设定的 feature.
        不实现也可以.
        """
        pass
