from abc import ABCMeta, abstractmethod
from typing import List, Optional

from ghoshell.ghost import Think, Stage, Thought, Event, Operator, OnActivating, OnReceived, Context


class SingleStageThink(Think, Stage, metaclass=ABCMeta):
    """
    单节点状态机.
    都是为了开发临时做的.
    """

    def all_stages(self) -> List[str]:
        return [""]

    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        if stage_name == "":
            return self
        return None

    def on_event(self, ctx: "Context", this: Thought, event: Event) -> Operator | None:
        if isinstance(event, OnActivating):
            return self.on_activate(ctx, this)
        elif isinstance(event, OnReceived):
            return self.on_received(ctx, this)
        return None

    @abstractmethod
    def on_activate(self, ctx: "Context", this: Thought) -> Operator | None:
        pass

    @abstractmethod
    def on_received(self, ctx: "Context", this: Thought) -> Operator | None:
        pass
