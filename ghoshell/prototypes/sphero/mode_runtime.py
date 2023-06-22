from __future__ import annotations

from typing import Optional, Dict, AnyStr, List

from pydantic import BaseModel, Field

from ghoshell.ghost import Context, Thought, ThinkMeta, URL
from ghoshell.ghost import Operator, Reaction, Intention
from ghoshell.ghost_fmk.thinks import SingleStageThink
from ghoshell.llms import OpenAIChatMsg
from ghoshell.messages import Text
from ghoshell.prototypes.sphero.sphero_ghost_core import SpheroGhostCore
from ghoshell.prototypes.sphero.sphero_messages import SpheroEventMessage


class SpheroRuntimeThought(Thought):
    priority = -1

    class Runtime(BaseModel):
        events: List[OpenAIChatMsg] = Field(default_factory=lambda: [])

    data: Runtime = Runtime()

    def prepare(self, args: Dict) -> None:
        self.data = self.Runtime()

    def set_variables(self, variables: Dict) -> None:
        self.data = self.Runtime(**variables)

    def vars(self) -> Dict | None:
        return self.data.dict()

    def _destroy(self) -> None:
        del self.data


class SpheroRuntimeModeThink(SingleStageThink):
    """
    runtime mode
    """

    def __init__(self, core: SpheroGhostCore):
        self._core = core
        self._config = core.config.runtime_mode

    def on_activate(self, ctx: "Context", this: SpheroRuntimeThought) -> Operator | None:
        self._core.say(ctx, this, self._config.on_activate)
        self._add_message(this, self._config.on_activate, False)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: SpheroRuntimeThought) -> Operator | None:
        """
        runtime 模式可能收到三种类型的消息.
        1. 命令被中断了.
        2. 命令运行完成.
        """
        # 自然语言消息.
        text = ctx.read(Text)
        if text is not None:
            if text.is_empty():
                return ctx.mind(this).rewind()
            return self._on_receive_text(ctx, this, text)

        # 事件类消息
        event = ctx.read(SpheroEventMessage)
        if event is not None:
            return self._on_receive_event(ctx, this, event)

        return ctx.mind(this).rewind()

    def _on_receive_text(self, ctx: Context, this: SpheroRuntimeThought, text: Text):
        pass

    def _on_receive_event(self, ctx: Context, this: SpheroRuntimeThought, event: SpheroEventMessage):
        pass

    @classmethod
    def _add_message(cls, this: SpheroRuntimeThought, message: str, from_user: bool) -> None:
        msg = OpenAIChatMsg(
            role=OpenAIChatMsg.ROLE_USER if from_user else OpenAIChatMsg.ROLE_ASSISTANT,
            content=message,
        )
        this.data.events.append(msg)

    def url(self) -> URL:
        return URL(resolver=self._config.name)

    def to_meta(self) -> ThinkMeta:
        return ThinkMeta(
            id=self._config.name,
            kind=self._core.config.driver_name,
        )

    def desc(self, ctx: Context, thought: Thought) -> AnyStr:
        return self._config.desc

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        return self.url().new_id()

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        return SpheroRuntimeThought(args)

    def result(self, ctx: Context, this: Thought) -> Optional[Dict]:
        return None

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {}
