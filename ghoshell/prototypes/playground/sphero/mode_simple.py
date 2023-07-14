from __future__ import annotations

from typing import Optional, Dict, AnyStr

from ghoshell.framework.thinks import SingleStageThink
from ghoshell.ghost import Context, Thought, ThinkMeta, URL, DictThought
from ghoshell.ghost import Operator, Reaction, Intention
from ghoshell.messages import Text
from ghoshell.prototypes.playground.sphero.sphero_ghost_core import SpheroGhostCore
from ghoshell.prototypes.playground.sphero.sphero_messages import SpheroCommandMessage


# --- simple mode--- #

class SpheroSimpleCommandModeThink(SingleStageThink):
    """
    简单命令模式.
    让 sphero 理解一次性输入的命令, 并且执行.
    用来做基准测试.
    """

    def __init__(self, core: SpheroGhostCore):
        self._core = core
        self._config = core.config.simple_mode

    def url(self) -> URL:
        return URL.new_think(self._config.name)

    def to_meta(self) -> ThinkMeta:
        return ThinkMeta(
            id=self._config.name,
            driver=self._core.config.driver_name,
        )

    def desc(self, ctx: Context, thought: Thought) -> AnyStr:
        return self._config.desc

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        return self.url().new_id()

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        thought = DictThought(args)
        thought.priority = -1
        return thought

    def result(self, ctx: Context, this: Thought) -> Optional[Dict]:
        return None

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {
            # "roll": RollCmdReaction(),
            # "stop": StopCmdReaction(),
        }

    def on_activate(self, ctx: "Context", this: Thought) -> Operator | None:
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: Thought) -> Operator | None:
        text = ctx.read(Text)
        if text is None or text.is_empty():
            return ctx.mind(this).rewind()

        message = SpheroCommandMessage()
        commands, ok = self._core.parse_direction(ctx, text.content)
        if not ok:
            ctx.send_at(this).err(self._core.config.unknown_order)
            return ctx.mind(this).rewind()

        message.commands = commands
        ctx.send_at(this).output(message)
        return ctx.mind(this).awaits()
