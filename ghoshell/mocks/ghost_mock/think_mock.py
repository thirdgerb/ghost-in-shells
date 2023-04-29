from typing import Optional, Any, ClassVar

from ghoshell.ghost import *
from ghoshell.ghost_fmk.reactions.commands import *
from ghoshell.ghost_fmk.stages import AwaitStage
from ghoshell.messages import *


class HelloWorldThink(Think, ThinkDriver):
    name: ClassVar[str] = "helloworld"

    def url(self) -> URL:
        return URL(resolver=self.name)

    def to_meta(self) -> ThinkMeta:
        return ThinkMeta(
            url=self.url().dict(),
            driver=self.driver_name(),
        )

    def driver_name(self) -> str:
        return HelloWorldThink.__name__

    def from_meta(self, meta: ThinkMeta) -> "Think":
        return self

    def description(self, thought: Thought) -> Any:
        return "hello world!"

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        return self.url().new_id()

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        return DictThought(args.copy())

    def result(self, this: Thought) -> Optional[Dict]:
        return None

    def all_stages(self) -> List[str]:
        return [""]

    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        if stage_name == "":
            return HelloWorldStage()
        return None


class HelloWorldStage(AwaitStage):

    def url(self) -> URL:
        return URL(resolver=HelloWorldThink.name, stage="")

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {
            "/helloworld": HelloWorldCmdReaction(),
            "/thought": ThoughtCmdReaction(),
            "/process": ProcessCmdReaction(),
            "/help": HelpCmdReaction(),
        }

    def on_received(self, ctx: "Context", this: Thought) -> Operator | None:
        text = ctx.read(Text)
        if text is not None:
            ctx.send_at(this).text(f"you said: {text}")
        ctx.send_at(this).text("I can only speak hello world! everyone!")
        return None

    def on_activating(self, ctx: "Context", this: Thought) -> Operator | None:
        ctx.send_at(this).text("hello world!")
        return ctx.mind(this).awaits()

    def on_quiting(self, ctx: "Context", this: Thought) -> Operator | None:
        ctx.send_at(this).text("I'm quiting")
        return None

    def on_canceling(self, ctx: "Context", this: Thought) -> Operator | None:
        ctx.send_at(this).text("I'm canceling!")
        return None

    def on_preempt(self, ctx: "Context", this: Thought) -> Operator | None:
        ctx.send_at(this).text("preempted!")
        return None
