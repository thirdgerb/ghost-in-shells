from __future__ import annotations

from typing import Optional, Any, ClassVar, Iterator

from ghoshell.framework.reactions.commands import *
from ghoshell.framework.stages import BasicStage
from ghoshell.ghost import *
from ghoshell.messages import *


class HelloWorldThink(Think, ThinkDriver):
    name: ClassVar[str] = "helloworld"

    def url(self) -> URL:
        return URL(think=self.name)

    def to_meta(self) -> Meta:
        return Meta(
            id=self.url().think,
            kind=self.meta_kind()
        )

    def preload_metas(self) -> Iterator[Meta]:
        return [self.to_meta()]

    def meta_kind(self) -> str:
        return HelloWorldThink.__name__

    def meta_config_json_schema(self) -> Dict:
        return {}

    def from_meta(self, meta) -> "Think":
        return self

    def desc(self, ctx: Context, thought: Thought) -> Any:
        return "hello world!"

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        return self.url().new_id()

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        return DictThought(args.copy())

    def result(self, ctx: "Context", this: Thought) -> Optional[Dict]:
        return None

    def all_stages(self) -> List[str]:
        return [""]

    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        if stage_name == "":
            return HelloWorldStage()
        return None


class HelloWorldStage(BasicStage):

    def url(self) -> URL:
        return URL(think=HelloWorldThink.name, stage="")

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {
            "/helloworld": HelloWorldCmdReaction(),
            "/thought": ThoughtCmdReaction(),
            "/process": ProcessCmdReaction(),
            # "/help": HelpCmdReaction(),
            "/redirect": RedirectCmdReaction(),
            "/task": TaskCmdReaction(),
            "/cancel": CancelCmdReaction(),
            "/quit": QuitCmdReaction(),
            "/instance_count": InstanceCountCmdReaction(),
        }

    def on_received(self, ctx: "Context", this: Thought, _) -> Operator | None:
        text = ctx.read(Text)
        if text is not None:
            ctx.send_at(this).text(f"you said: {text}")
        ctx.send_at(this).text("I can only speak hello world! everyone!")
        return None

    def on_activating(self, ctx: "Context", this: Thought, _) -> Operator | None:
        ctx.send_at(this).text(HelloWorldStage.__name__ + ":hello world!")
        return ctx.mind(this).awaits(to=URL(think="conversational"))

    def on_quiting(self, ctx: "Context", this: Thought, _) -> Operator | None:
        ctx.send_at(this).text(HelloWorldStage.__name__ + ":I'm quiting")
        return None

    def on_canceling(self, ctx: "Context", this: Thought, _) -> Operator | None:
        ctx.send_at(this).text(HelloWorldStage.__name__ + ":I'm canceling!")
        return None

    def on_preempt(self, ctx: "Context", this: Thought, _) -> Operator | None:
        ctx.send_at(this).text(HelloWorldStage.__name__ + ":preempted!")
        return ctx.mind(this).awaits()
