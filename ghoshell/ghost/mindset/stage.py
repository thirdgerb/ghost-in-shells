from __future__ import annotations

from abc import abstractmethod
from typing import List

from ghoshell.ghost.context import Context
from ghoshell.ghost.mindset.events import *
from ghoshell.ghost.mindset.focus import Intention
from ghoshell.ghost.mindset.operator import Operator
from ghoshell.ghost.mindset.thought import Thought
from ghoshell.ghost.url import URL


class Stage(metaclass=ABCMeta):
    """
    Thinking 的状态位.
    状态位有一些基本的类型, 可以分为两大类:
    1. 中断的状态位, 等待
    """

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
    def react(self, ctx: Context, this: Thought) -> Operator:
        pass

#
# class ReactionStage(Stage, metaclass=ABCMeta):
#     """
#     自身不会发生状态变更的特殊 Stage, 只是用来做响应.
#     """
#
#     @abstractmethod
#     def react(self, ctx: "Context", this: Thought, params: Dict | None):
#         pass
#
#     def on_receive(self, ctx: "Context", this: Thought, event: Receiving) -> Operator | None:
#         op = self.react(ctx, this, event.matched)
#         if op is None:
#             return ctx.mind(this).rewind()
#         return op
#
#     def activate(self, ctx: "Context", this: Thought, event: Activating) -> Operator:
#         # todo
#         raise RuntimeException("todo")
#
#     def on_preempt(self, ctx: "Context", this: Thought, event: Preempting) -> Operator | None:
#         return None
#
#     def on_callback(self, ctx: "Context", this: Thought, event: Callback) -> Operator | None:
#         return None
#
#     def on_withdraw(self, ctx: "Context", this: Thought, event: Withdrawing) -> Operator | None:
#         return None
