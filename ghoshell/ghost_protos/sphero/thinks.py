from __future__ import annotations

from typing import Optional, Dict, AnyStr, ClassVar

import yaml
from pydantic import Field

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


class LearningModeOutput(BaseModel):
    """
    多轮对话模式下每一轮的输出.
    """

    reply: str  # 本轮回复的内容.
    direction: str | None = None  # 添加的命令.
    run: str | None = None  # 本轮需要执行的命令.
    test: bool = False
    title: str = ""
    save: bool = False
    finished: bool = False  # 当前模式是否结束


class SpheroThinkDriver(ThinkDriver):
    """
    driver sphero gpt
    """

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
                return SpheroLearningModeThink(self)
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

    @classmethod
    def unpack_commands_in_direction(cls, text: str) -> SpheroCommandMessage:
        """
        解析 llm 通过 yaml 形式返回的 commands.
        """
        result = SpheroCommandMessage(direction=text)
        command_data = yaml.safe_load(text)
        if not isinstance(command_data, list):
            raise RuntimeException(f"invalid ghost response: {text}")
        for detail in command_data:
            result.commands.append(detail)
        return result

    @classmethod
    def unpack_learning_mode_resp(cls, text: str) -> LearningModeOutput:
        data = yaml.safe_load(text)
        return LearningModeOutput(**data)

    @classmethod
    def get_prompter(cls, ctx: Context) -> LLMPrompter:
        return ctx.container.force_fetch(LLMPrompter)

    @classmethod
    def say(cls, ctx: Context, this: Thought, text: str) -> None:
        msg = SpheroCommandMessage.new(Say(text=text))
        ctx.send_at(this).output(msg)


class SpheroMainModeThink(SingleStageThink):
    """
    主场景. 可以接受命令进入另外两种模式.
    """

    def __init__(self, driver: SpheroThinkDriver):
        self._driver = driver
        self._config = driver.config.main_mode


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
        self._driver.say(ctx, this, self._config.on_activate)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: Thought) -> Operator | None:
        text = ctx.read(Text)
        if text is None or text.is_empty():
            return ctx.mind(this).rewind()
        prompt = self._config.prompt(
            self._config.instruction,
            text.content,
        )
        prompter = self._driver.get_prompter(ctx)
        resp = prompter.prompt(prompt)
        if resp == self._config.invalid_mark:
            ctx.send_at(this).err(self._config.unknown_order)
            return ctx.mind(this).rewind()
        if self._config.debug:
            ctx.send_at(this).markdown(f"""
# debug mode show prompt resp

{resp}
""")
        message = self._driver.unpack_commands_in_direction(resp)

        ctx.send_at(this).output(message)
        return ctx.mind(this).awaits()


class LearningModeThought(Thought):
    """
    学习模式的思维结构.
    """

    priority = -1

    class Data(BaseModel):
        round: int = 0
        directions: List[str] = Field(default_factory=lambda: [])
        commands: Dict[int, List[Dict]] = Field(default_factory=lambda: {})
        title: str = ""

    data: Data = Data()

    def prepare(self, args: Dict) -> None:
        return

    def set_variables(self, variables: Dict) -> None:
        self.data = self.Data(**variables)

    def vars(self) -> Dict | None:
        return self.data.dict()

    def _destroy(self) -> None:
        return


# --- conversational mode


class SpheroLearningModeThink(SingleStageThink):
    """
    多轮对话模式, 支持教学, 技能记忆等等等.
    需要实现的基本功能:
    1. welcome: 自我介绍
    2. 将理解的自然语言指令记录到上下文中.
    3. 测试: 将上下文中的自然语言指令, 生成为一组命令. 然后运行.
    4. 保存为技能: 将当前上下文中形成的指令, 保存为一个技能. 需要用户提供技能的名称.
    5. 要返回
    """

    def __init__(self, driver: SpheroThinkDriver):
        self._driver = driver
        self._config: SpheroLearningModeConfig = driver.config.conversational_mode

    def on_activate(self, ctx: "Context", this: LearningModeThought) -> Operator | None:
        self._driver.say(ctx, this, self._config.on_activate)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: LearningModeThought) -> Operator | None:
        text = ctx.read(Text)
        if text is None or text.is_empty():
            return ctx.mind(this).rewind()
        this.data.round += 1
        prompt = self._config.turn_prompt(
            n=this.data.round,
            commands=this.data.directions,
            direction=text.content,
        )
        prompter = self._driver.get_prompter(ctx)
        resp = prompter.prompt(prompt)
        parsed = self._driver.unpack_learning_mode_resp(resp)
        return self._receive_parsed_output(ctx, parsed, this)

    def _receive_parsed_output(self, ctx: Context, parsed: LearningModeOutput, this: LearningModeThought) -> Operator:
        ctx.send_at(this).json(parsed.dict())
        # if parsed.title:
        #     this.data.title = parsed.title
        # if parsed.direction:
        #     this.data.commands.append(parsed.direction)
        # if parsed.test:
        # if parsed.finished:
        #     return ctx.mind(this).finish()
        return ctx.mind(this).awaits()

    def url(self) -> URL:
        return URL.new_resolver(self._config.name)

    def to_meta(self) -> ThinkMeta:
        return ThinkMeta(
            id=self._config.name,
            kind=self._driver.driver_name(),
        )

    def description(self, thought: Thought) -> AnyStr:
        return self._config.desc

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        return self.url().new_id()

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        return LearningModeThought(args)

    def result(self, ctx: Context, this: LearningModeThought) -> Optional[Dict]:
        return None

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {}


# --- reactions

class RollCmdReaction(CommandReaction):
    """
    滚动的命令
    """

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
    """
    停止转动的命令.
    """

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
