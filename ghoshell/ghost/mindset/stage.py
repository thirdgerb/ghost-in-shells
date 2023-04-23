from __future__ import annotations

from abc import abstractmethod
from typing import List

from ghoshell.ghost.context import Context
from ghoshell.ghost.intention import Intention
from ghoshell.ghost.mindset.events import *
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
        pass

    @abstractmethod
    def on_await(self, ctx: Context) -> List[URL] | None:
        """
        只有 await 时才会调用的方法.
        """
        pass

    @abstractmethod
    def on_event(self, ctx: "Context", this: Thought, event: Event) -> Operator | None:
        """
        如果已经被激活过, 则不会再被激活.
        """
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
