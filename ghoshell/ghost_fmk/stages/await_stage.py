from abc import ABCMeta, abstractmethod

from ghoshell.ghost import *


# 为一些最常见的节点提供开发范式.

class AwaitStage(Stage, metaclass=ABCMeta):
    """
    一个等待节点的实例, 很简单的等待节点.
    作为示范.
    """

    def on_event(self, ctx: "Context", this: Thought, event: Event) -> Operator | None:
        if isinstance(event, OnActivating):
            return self.on_activating(ctx, this, event)
        if isinstance(event, OnReceived):
            received = self.on_received(ctx, this, event)
            if received is None:
                return ctx.mind(this).awaits()
        if isinstance(event, OnCanceling):
            op = self.on_canceling(ctx, this, event)
            if op is None:
                return self.on_withdrawing(ctx, this, event)
        if isinstance(event, OnQuiting):
            op = self.on_quiting(ctx, this, event)
            if op is None:
                return self.on_withdrawing(ctx, this, event)
        if isinstance(event, OnPreempted):
            op = self.on_preempt(ctx, this, event)
            if op is None:
                return self.on_activating(ctx, this, event)
        return None

    @abstractmethod
    def on_received(self, ctx: "Context", this: Thought, e: OnReceived) -> Operator | None:
        pass

    @abstractmethod
    def on_activating(self, ctx: "Context", this: Thought, e: Event) -> Operator | None:
        pass

    @abstractmethod
    def on_quiting(self, ctx: "Context", this: Thought, e: OnQuiting) -> Operator | None:
        pass

    @abstractmethod
    def on_canceling(self, ctx: "Context", this: Thought, e: OnCanceling) -> Operator | None:
        pass

    @abstractmethod
    def on_preempt(self, ctx: "Context", this: Thought, e: OnPreempted) -> Operator | None:
        pass

    def on_withdrawing(self, ctx: "Context", this: Thought, e: OnWithdrawing) -> Operator | None:
        return None


