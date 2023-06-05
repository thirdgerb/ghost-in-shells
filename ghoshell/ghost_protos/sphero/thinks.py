from __future__ import annotations

from typing import Optional, List, Dict, AnyStr, ClassVar

import yaml

from ghoshell.ghost import MindsetNotFoundException, Operator, Reaction, Intention
from ghoshell.ghost import RuntimeException, TaskLevel
from ghoshell.ghost import Think, Context, Thought, ThinkMeta, URL, ThinkDriver, DictThought
from ghoshell.ghost_fmk.intentions import CommandOutput
from ghoshell.ghost_fmk.reactions import CommandReaction, Command
from ghoshell.ghost_fmk.thinks import SingleStageThink
from ghoshell.ghost_protos.sphero.configs import *
from ghoshell.ghost_protos.sphero.messages import SpheroCommandMessage, Roll, Say, Stop
from ghoshell.llms import LLMPrompter
from ghoshell.messages import Text


class SpheroThinkDriver(ThinkDriver):
    sphero_driver_name: ClassVar[str] = "sphero_thinks"

    def __init__(self, config: SpheroThinkConfig):
        self.config = config

    def driver_name(self) -> str:
        return self.sphero_driver_name

    def from_meta(self, meta: ThinkMeta) -> "Think":
        match meta.id:
            case self.config.simple_command_mode.name:
                return SpheroSimpleCommandModeThink(self)
            case self.config.conversational_mode.name:
                return SpheroConversationalModeThink(self)
            case _:
                raise MindsetNotFoundException(f"think {meta.id} not found")

    def to_metas(self) -> List[ThinkMeta]:
        result = []
        modes = [
            self.config.simple_command_mode.name,
            self.config.conversational_mode.name,
        ]
        for think_name in modes:
            result.append(ThinkMeta(
                kind=self.driver_name(),
                id=think_name,
            ))
        return result


class SpheroSimpleCommandModeThink(SingleStageThink):
    """
    简单命令模式.
    让 sphero 理解一次性输入的命令, 并且执行.
    """

    def __init__(self, driver: SpheroThinkDriver):
        self._driver = driver
        self._config = driver.config.simple_command_mode

    def url(self) -> URL:
        return URL.new_resolver(self._config.name)

    def to_meta(self) -> ThinkMeta:
        return ThinkMeta(
            id=self._config.name,
            driver=SpheroThinkDriver.sphero_driver_name,
        )

    def description(self, thought: Thought) -> AnyStr:
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
            "roll": RollCmdReaction(),
            "stop": StopCmdReaction(),
        }

    def on_activate(self, ctx: "Context", this: Thought) -> Operator | None:
        msg = SpheroCommandMessage.new(Say(text=self._config.welcome))
        ctx.send_at(this).output(msg)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: Thought) -> Operator | None:
        text = ctx.read(Text)
        if text is None or text.is_empty():
            return ctx.mind(this).rewind()
        prompt = self._config.prompt(
            self._config.instruction,
            text.content,
        )
        if self._config.debug:
            ctx.send_at(this).markdown(f"""
# debug mode show prompt

{prompt}
""")
        prompter = ctx.container.force_fetch(LLMPrompter)
        resp = prompter.prompt(prompt)
        if resp == "no":
            ctx.send_at(this).err(self._config.unknown_order)
            return ctx.mind(this).rewind()
        if self._config.debug:
            ctx.send_at(this).markdown(f"""
# debug mode show prompt resp

{resp}
""")
        message = self._unpack_yaml_commands(resp)
        ctx.send_at(this).output(message)
        return ctx.mind(this).awaits()

    def _unpack_yaml_commands(self, text: str) -> SpheroCommandMessage:
        result = SpheroCommandMessage()
        command_data = yaml.safe_load(text)
        if not isinstance(command_data, list):
            raise RuntimeException(f"invalid ghost response: {text}")
        for detail in command_data:
            result.commands.append(detail)
        return result


class SpheroConversationalModeThink(SingleStageThink):
    """
    多轮对话模式, 支持教学, 技能记忆等等等.
    """

    def __init__(self, driver: SpheroThinkDriver):
        self._driver = driver
        self._config = driver.config.conversational_mode


class RollCmdReaction(CommandReaction):

    def __init__(self):
        super().__init__(
            cmd=Command(
                name="roll",
                desc="make sphero roll",
                opts=[
                    dict(
                        name="speed",
                        desc="rolling speed",
                        short="s",
                        default=100,
                    ),
                    dict(
                        name="duration",
                        desc="rolling seconds",
                        short="d",
                        default=1,
                    ),
                    dict(
                        name="heading",
                        desc="rolling heading angle",
                        short="a",
                        default=0,
                    ),
                ],
            ),
            level=TaskLevel.LEVEL_PRIVATE,
        )

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        heading = int(output.params.get("heading", 0))
        speed = int(output.params.get("speed", 100))
        duration = float(output.params.get("duration", 1))

        direction = SpheroCommandMessage()
        direction.add(Roll(
            heading=heading,
            speed=speed,
            duration=duration,
        ))
        ctx.send_at(this).output(direction)
        return ctx.mind(this).rewind()


class StopCmdReaction(CommandReaction):

    def __init__(self):
        super().__init__(
            cmd=Command(
                name="stop",
                desc="stop sphero",
            ),
            level=TaskLevel.LEVEL_PRIVATE,
        )

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        direction = SpheroCommandMessage()
        direction.add(Stop(duration=1))
        ctx.send_at(this).output(direction)
        return ctx.mind(this).rewind()
