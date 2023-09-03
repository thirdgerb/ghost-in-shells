from __future__ import annotations

from typing import Optional, AnyStr, Type

from ghoshell.framework.reactions import system_cmds
from ghoshell.prototypes.playground.werewolf.stages import *
from ghoshell.prototypes.playground.werewolf.thought import WerewolfGameThought

WEREWOLF_GAME_KIND = "playground/werewolf_game_kind"


class WerewolfGameThink(Think, Stage):
    _stages: List[Type[AbsWerewolfGameStage]] = [
        GameInitStage,
        AskUserJoinStage,
        GameStartStage,
    ]

    def __init__(self, config: WerewolfGameConfig):
        self._config = config
        self._stage_classes = {s.name(): s for s in self._stages}

    def url(self) -> URL:
        return URL.new(self._config.think)

    def to_meta(self) -> Meta:
        return Meta(
            id=self._config.name,
            kind=WEREWOLF_GAME_KIND,
            config=self._config.model_dump()
        )

    def desc(self, ctx: Context, thought: Thought | None) -> AnyStr:
        return self._config.desc

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        # 以后再解决记忆等问题.
        return self.url().new_id()

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        return WerewolfGameThought(args)

    def result(self, ctx: Context, this: Thought) -> Optional[Dict]:
        return None

    def all_stages(self) -> List[str]:
        return list(self._stage_classes.keys())

    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        if not stage_name:
            return self
        if stage_name in self._stage_classes:
            return self._stage_classes[stage_name](self._config)

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        # todo: 增加 debug 命令.
        return system_cmds

    def on_event(self, ctx: "Context", this: Thought, event: Event) -> Operator | None:
        ctx.send_at(this).markdown(self._config.speech.welcome)
        return ctx.mind(this).forward(GameInitStage.name())
