from __future__ import annotations

from typing import List

from ghoshell.ghost.context import Context
from ghoshell.ghost.exceptions import RuntimeException
from ghoshell.ghost.mindset.events import *
from ghoshell.ghost.mindset.thought import Thought
from ghoshell.ghost.operator import Operator
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
    def description(self, this: Thought) -> str:
        pass

    @abstractmethod
    def intentions(self, ctx: Context) -> List[Intention] | None:
        pass

    @abstractmethod
    def activate(self, ctx: "Context", this: Thought, event: Activating) -> Operator:
        """
        stage 切换时执行的逻辑, 是 stage 的主动逻辑.
        activate 只发生在思维重定向操作后.
        如果已经被激活过, 则不会再被激活.
        """
        pass

    @abstractmethod
    def on_preempt(self, ctx: "Context", this: Thought, event: Preempting) -> Operator | None:
        pass

    @abstractmethod
    def on_callback(self, ctx: "Context", this: Thought, event: Callback) -> Operator | None:
        pass

    @abstractmethod
    def on_withdraw(self, ctx: "Context", this: Thought, event: Withdrawing) -> Operator | None:
        pass

    @abstractmethod
    def on_receive(self, ctx: "Context", this: Thought, event: Receiving) -> Operator | None:
        pass


class ReactionStage(Stage, metaclass=ABCMeta):
    """
    自身不会发生状态变更的特殊 Stage, 只是用来做响应.
    """

    @abstractmethod
    def react(self, ctx: "Context", this: Thought, params: Dict | None):
        pass

    def on_receive(self, ctx: "Context", this: Thought, event: Receiving) -> Operator | None:
        op = self.react(ctx, this, event.matched)
        if op is None:
            return ctx.mind(this).rewind()
        return op

    def activate(self, ctx: "Context", this: Thought, event: Activating) -> Operator:
        # todo
        raise RuntimeException("todo")

    def on_preempt(self, ctx: "Context", this: Thought, event: Preempting) -> Operator | None:
        return None

    def on_callback(self, ctx: "Context", this: Thought, event: Callback) -> Operator | None:
        return None

    def on_withdraw(self, ctx: "Context", this: Thought, event: Withdrawing) -> Operator | None:
        return None
