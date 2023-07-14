from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, Optional, TYPE_CHECKING, List, TypeVar, Type, ClassVar

from pydantic import BaseModel

from ghoshell.messages import Message, Input, Output

if TYPE_CHECKING:
    from ghoshell.ghost.ghost import Clone
    from ghoshell.ghost.mindset import Thought, Mind
    from ghoshell.ghost.sending import Sender
    from ghoshell.ghost.session import Session
    from ghoshell.ghost.runtime import Runtime
    from ghoshell.container import Container

M = TypeVar('M', bound=Message)


class Context(metaclass=ABCMeta):
    """
    Ghost 运行时, 每一条输入消息 (message) 触发的处理上下文.
    Context 主要包含单条输入消息处理时所需要的各种系统模块.
    """

    @property
    @abstractmethod
    def input(self) -> "Input":
        """
        请求的输入消息, 不应该被外部行为变更.
        注意: 要处理好指针的问题, 避免全局污染
        """
        pass

    @property
    @abstractmethod
    def clone(self) -> "Clone":
        """
        当前上下文中运行的 Ghost 的分身.
        对于不同的用户而言, 看到的可能是 Ghost 的一个分身个体.
        """
        pass

    @property
    @abstractmethod
    def container(self) -> "Container":
        """
        提供面向接口的容器, 可以通过容器获取各种组件.
        """
        pass

    @property
    @abstractmethod
    def runtime(self) -> "Runtime":
        """
        Clone 的运行时, 每个 Clone 运行时可以处理多个任务
        多个任务之间构成了各种关系, 这些关系决定了每个任务 结束/取消/失败 时的回调方向.
        """
        pass

    @property
    @abstractmethod
    def session(self) -> "Session":
        """
        Session 主要用来管理会话本身产生的 I/O 流.
        """
        pass

    @abstractmethod
    def mind(self, this: Optional["Thought"]) -> "Mind":
        """
        任务调度的核心方法, 可以立足于一个任务, 调度它 重定向/依赖/取消 等等.
        如果 this 为 None, 则操作对象为当前任务.
        """
        pass

    @abstractmethod
    def read(self, expect: Type[M]) -> M | None:
        """
        从上下文中读取一个 Message 的消息.
        会根据 Message 的类型进行自主匹配.
        """
        pass

    @abstractmethod
    def send_at(self, _with: Optional["Thought"]) -> "Sender":
        """
        发送消息的方法.
        以一个 Thought 为基础, 发出各种消息体给 Shell
        """
        pass

    @abstractmethod
    def set_input(self, _input: "Input") -> None:
        """
        通过 set_input 可以强行变更当前上下文.
        后续所有的逻辑都会受影响. 通常是用在中间件中.
        """
        pass

    @abstractmethod
    def async_input(self, _input: "Input") -> None:
        """
        ghost 给 ghost 发送信息时使用
        pid 为 None, Trace 为 None 时, 默认是发送给当前 Clone 自己.
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
        请求级别的上下文缓存, 用在内存中.
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        从请求级别的上下文中获取缓存
        """
        pass

    @abstractmethod
    def fail(self) -> None:
        pass

    @abstractmethod
    def finish(self) -> None:
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


class ContextValue(BaseModel, metaclass=ABCMeta):
    """
    上下文可以用来存取强类型约束的数据.
    这里给出一个示范.
    """

    key: ClassVar[str] = "key"

    @classmethod
    def get(cls, ctx: Context) -> ContextValue | None:
        value = ctx.get(cls.key)
        if value is None:
            return None
        return cls(**value)

    def set(self, ctx: Context) -> None:
        ctx.set(self.key, self.model_dump())
