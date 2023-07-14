from __future__ import annotations

from abc import abstractmethod, ABCMeta
from typing import List

from ghoshell.ghost.context import Context
from ghoshell.ghost.mindset.events import Event
from ghoshell.ghost.mindset.focus import Intention
from ghoshell.ghost.mindset.operator import Operator
from ghoshell.ghost.mindset.thought import Thought
from ghoshell.url import URL


class Stage(metaclass=ABCMeta):
    """
    Think 作为一个有限状态机, Stage 是它的状态位.
    """

    def desc(self, ctx: Context, this: Thought | None) -> str:
        """
        stage 的自我描述, 通常用于 LLM
        """
        return ""

    @abstractmethod
    def url(self) -> URL:
        pass

    @abstractmethod
    def intentions(self, ctx: Context) -> List[Intention] | None:
        """
        可被命中的意图. 用于重定向.
        """
        pass

    @abstractmethod
    def reactions(self) -> Dict[str, Reaction]:
        """
        当 Stage 进入 Waiting 状态时, 注册的各种响应逻辑.
        和多任务调度无关. 用特殊的方式实现.
        """
        pass

    @abstractmethod
    def on_event(self, ctx: "Context", this: Thought, event: Event) -> Operator | None:
        """
        触发调度事件
        """
        pass

    def __repr__(self):
        return f"stage:[{self.url()}]"


class Reaction(metaclass=ABCMeta):
    """
    Stage 在 WAITING 状态可以做的动作, 类似面向对象的 methods
    """

    @abstractmethod
    def level(self) -> int:
        """
        动作的级别, 对标 TaskLevel
        Private: 只有当前任务是 process.awaiting 时才可以响应.
        """
        pass

    @abstractmethod
    def intentions(self, ctx: Context) -> List[Intention]:
        pass

    @abstractmethod
    def react(self, ctx: Context, this: Thought, params: Dict | None) -> Operator | None:
        pass
