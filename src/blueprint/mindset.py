from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Callable

if TYPE_CHECKING:
    from typing import Optional, List
    from .intention import Intention
    from .context import Context
    from .operator import Operator
    from .url import URL

    T_ARG = TypeVar('T_ARG', bound=object)
    T_DATA = TypeVar('T_DATA', bound=object)
    T_RESULT = TypeVar('T_RESULT', bound=object)
    BEHAVE = Callable[[Context], None]


class This(metaclass=ABCMeta):
    args: T_ARG
    data: T_DATA
    status: int = 0
    result: Optional[T_RESULT] = None
    priority: float = 0
    overdue: int = -1


class Thinking(metaclass=ABCMeta):
    """
    ghost 拥有的思维模块
    """

    @property
    @abstractmethod
    def uml(self) -> URL:
        """
        用类似 url (uniform resource locator) 的方式定位一个 Thinking
        soul: 对应的 soul, 用 a.b.c 的方式定位
        path: 对应的 Thinking, 用 /a/b/c 的方式定位
        state: 对应的状态, 用 #fragment/a/b 的方式定位
        args: 原始的入参.
        """
        pass

    @property
    @abstractmethod
    def stateless(self) -> bool:
        """
        表示当前状态是否要导致 thought 状态变更.
        状态变更的同时会产生新的 attentions
        """
        pass

    @abstractmethod
    def identity(self, ctx: Context, args: T_ARG) -> str:
        """
        结合上下文生成 identity, 用来从 runtime 里查找到 thought
        """
        pass

    @abstractmethod
    def create(self, ctx: Context, args: T_ARG) -> This:
        """
        结合上下文, 初始化一个 thought, 以加入 runtime 中运行.
        """
        pass

    @abstractmethod
    def intentions(self, this: This) -> List[Intention]:
        """
        进入当前状态可以提供的各种意图.
        """
        pass

    @abstractmethod
    def attentions(self, this: This, ctx: Context) -> List[URL]:
        """
        从当前状态进入别的状态的连接点
        attentions with intentions
        """
        pass

    @abstractmethod
    def react(self, this: This, ctx: Context) -> Operator:
        """
        正式进入当前状态后, 会发生的行为.
        """
        pass

    @abstractmethod
    def fallback(self, this: This, ctx: Context) -> Operator:
        """
        如果一个事件没有 intention 去响应
        就会 fallback 到当前状态来尝试兜底响应.
        """
        pass

    @abstractmethod
    def on_event(self, this: This, ctx: Context, op: Operator) -> Operator:
        """
        当一个事件执行到当前位置时, 可以在它执行之前进行拦截
        做必要的动作.
        常见的事件: 依赖回调, 取消, 退出, 异常等.
        """
        pass


class Mindset(metaclass=ABCMeta):
    """
    定义了 Ghost 拥有的思维方式
    核心是可以通过 UniformReactionLocator 取出 Reaction
    """

    @abstractmethod
    def fetch(self, uml: URL) -> Optional[Thinking]:
        pass

    @abstractmethod
    def register(self, uml: URL, thinking: Thinking) -> None:
        pass
