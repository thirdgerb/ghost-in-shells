from __future__ import annotations

import os
from typing import Optional, Dict, AnyStr, ClassVar, Tuple

import yaml
from pydantic import Field

from ghoshell.ghost import MindsetNotFoundException, Operator, Reaction, Intention
from ghoshell.ghost import RuntimeException, TaskLevel
from ghoshell.ghost import Think, Context, Thought, ThinkMeta, URL, ThinkDriver, DictThought
from ghoshell.ghost_fmk.intentions import CommandOutput
from ghoshell.ghost_fmk.reactions import CommandReaction, Command
from ghoshell.ghost_fmk.reactions.commands import ProcessCmdReaction
from ghoshell.ghost_fmk.thinks import SingleStageThink
from ghoshell.ghost_protos.sphero.configs import *
from ghoshell.ghost_protos.sphero.messages import SpheroCommandMessage, Roll, Say, Stop
from ghoshell.llms import LLMTextCompletion
from ghoshell.messages import Text


class LearningModeOutput(BaseModel):
    """
    多轮对话模式下每一轮的输出.
    """

    reply: str  # 本轮回复的内容.
    title: str | None = None  # 技能的名称
    directions: List[str] = Field(default_factory=lambda: [])
    reaction: str | None = None  # 本轮对话执行的动作.


class SpheroCommandsCache(BaseModel):
    """
    做一个假的本地 cache, 方便测试时重复使用指令但不用每次都去 prompt.
    """

    # 命令的索引.
    indexes: Dict[str, List[Dict]] = Field(default_factory=lambda: {})


class SpheroThinkDriver(ThinkDriver):
    """
    driver sphero gpt
    """

    sphero_driver_name: ClassVar[str] = "sphero_thinks"

    def __init__(self, runtime_path: str, config: SpheroGhostConfig):
        self.app_runtime_path = runtime_path
        self.config = config
        self._cached_commands: SpheroCommandsCache = SpheroCommandsCache()
        self._load_commands()

    def _load_commands(self):
        filename = self._cached_commands_file()
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                yaml.safe_dump(dict(), f)
        with open(filename) as f:
            data = yaml.safe_load(f)
            self._cached_commands = SpheroCommandsCache(**data)

    def _cached_commands_file(self) -> str:
        return "/".join([
            self.app_runtime_path.rstrip("/"),
            self.config.relative_runtime_path.strip("/"),
            "/commands.yaml",
        ])

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
    def _unpack_commands_in_direction(cls, message: SpheroCommandMessage, text: str) -> SpheroCommandMessage:
        """
        解析 llm 通过 yaml 形式返回的 commands.
        """
        if text.startswith("`") or text.endswith("`"):
            text.strip("`")

        command_data = yaml.safe_load(text)
        if not isinstance(command_data, list):
            raise RuntimeException(f"invalid ghost response: {text}")
        for detail in command_data:
            message.commands.append(detail)
        return message

    @classmethod
    def unpack_learning_mode_resp(cls, text: str) -> LearningModeOutput:
        text = text.strip("`")
        data = yaml.safe_load(text)
        return LearningModeOutput(**data)

    @classmethod
    def get_prompter(cls, ctx: Context) -> LLMTextCompletion:
        return ctx.container.force_fetch(LLMTextCompletion)

    @classmethod
    def say(cls, ctx: Context, this: Thought, text: str) -> None:
        msg = SpheroCommandMessage.new(Say(text=text))
        ctx.send_at(this).output(msg)

    def cache_command(self, command_str: str, message: SpheroCommandMessage) -> None:
        self._cached_commands.indexes[command_str] = message.commands.copy()
        self._save_cached()

    def parse_command(
            self,
            command_str: str,
            prompter: LLMTextCompletion,
            message: SpheroCommandMessage,
    ) -> Tuple[SpheroCommandMessage, bool]:
        """
        指令不适合用 embedding 索引, 否则仍然需要调用一次 llm 接口, 来让 llm 判断是否一致.
        因此先尝试用完整的.
        """
        if command_str in self._cached_commands.indexes:
            command_data = self._cached_commands.indexes[command_str]
            message.commands = command_data
            return message, True
        else:
            prompt = self.config.command_prompt(command_str)
            resp = prompter.text_completion(prompt)
            if resp == self.config.invalid_mark:
                return message, False
            message = self._unpack_commands_in_direction(message, resp)
            self._cached_commands.indexes[command_str] = message.commands.copy()
            self._save_cached()
            return message, True

    def _save_cached(self):
        filename = self._cached_commands_file()
        with open(filename, 'w') as f:
            yaml.safe_dump(self._cached_commands.dict(), f, allow_unicode=True)

    def get_dialog_sep(self) -> str:
        return self.config.dialog_sep


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
        prompter = self._driver.get_prompter(ctx)
        message = SpheroCommandMessage()
        message, ok = self._driver.parse_command(text.content, prompter, message)
        if not ok:
            ctx.send_at(this).err(self._config.unknown_order)
            return ctx.mind(this).rewind()
        ctx.send_at(this).output(message)
        return ctx.mind(this).awaits()


class DialogMessage(BaseModel):
    """
    多轮对话消息.
    """
    role: str
    text: str


class LearningModeThought(Thought):
    """
    学习模式的思维结构.
    """

    priority = -1

    class Data(BaseModel):
        max_turns: int = 2
        round: int = 0
        dialog: List[DialogMessage] = Field(default_factory=lambda: [])
        directions: List[str] = Field(default_factory=lambda: [])
        title: str = ""

    data: Data = Data()

    def add_message(self, role: str, message: str):
        self.data.dialog.append(DialogMessage(
            role=role,
            text=message,
        ))
        max_lines = self.data.max_turns * 2
        exists_lines = len(self.data.dialog)
        if exists_lines > max_lines:
            self.data.dialog = self.data.dialog[exists_lines - max_lines:]

    def join_conversation(self, sep: str) -> str:
        dialog = []
        for message in self.data.dialog:
            dialog.append(f"{message.role}: ={sep}= {message.text} ={sep}=")
        return "\n\n".join(dialog)

    def prepare(self, args: Dict) -> None:
        return

    def set_variables(self, variables: Dict) -> None:
        self.data = self.Data(**variables)

    def vars(self) -> Dict | None:
        return self.data.dict()

    def _destroy(self) -> None:
        return


# --- conversational mode
#
# class SpheroLearningModeToolsReaction(LLMToolReaction):
#
#     def __init__(self):
#         super().__init__({
#             "quit": "退出当前模式",
#             "finish": "结束学习模式",
#             "test": "测试或者直接运行系统",
#         })
#
#     def on_match(self, ctx: Context, this: LearningModeThought, result: LLMToolIntentionResult) -> Operator | None:
#         print(result)
#         return None


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
        this.add_message(self._config.ai_role, self._config.on_activate)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: LearningModeThought) -> Operator | None:
        text = ctx.read(Text)
        if text is None or text.is_empty():
            return ctx.mind(this).rewind()
        this.data.round += 1

        prompt = self._config.turn_prompt(
            title=this.data.title,
            conversation=this.join_conversation(self._driver.get_dialog_sep()),
            directions=this.data.directions,
            user_message=text.content,
            max_turns=self._config.max_turns * 2,
            sep=self._driver.get_dialog_sep(),
        )

        this.add_message(self._config.user_role, text.content)
        prompter = self._driver.get_prompter(ctx)
        resp = prompter.text_completion(prompt)
        parsed = self._driver.unpack_learning_mode_resp(resp)
        return self._receive_parsed_output(ctx, parsed, this)

    def _receive_parsed_output(self, ctx: Context, parsed: LearningModeOutput, this: LearningModeThought) -> Operator:
        if self._config.debug:
            ctx.send_at(this).json(parsed.dict())

        # 完成赋值.
        if parsed.title:
            this.data.title = parsed.title
        if parsed.directions:
            this.data.directions = parsed.directions

        # 解决 title 为空的问题.
        if parsed.reaction == "save":
            if not this.data.title:
                self._driver.say(ctx, this, self._config.ask_for_title)
                this.add_message(self._config.ai_role, self._config.ask_for_title)
                return ctx.mind(this).awaits()

        # 发送消息.
        if parsed.reply:
            reply = parsed.reply
            self._driver.say(ctx, this, reply)
            this.add_message(self._config.ai_role, reply)

        match parsed.reaction:
            case "restart":
                return ctx.mind(this).restart()
            case "test":
                return self._run_test(ctx, this)
            case "save":
                return self._save_case(ctx, this)
            case "finish":
                return ctx.mind(this).finish()
            case _:
                return ctx.mind(this).awaits()

    def _save_case(self, ctx: Context, this: LearningModeThought) -> Operator:
        message = SpheroCommandMessage()
        prompter = ctx.container.force_fetch(LLMTextCompletion)
        for direction in this.data.directions:
            self._driver.parse_command(direction, prompter, message)
        self._driver.cache_command(this.data.title, message)
        return ctx.mind(this).awaits()

    def _run_test(self, ctx: Context, this: LearningModeThought) -> Operator:
        message = SpheroCommandMessage()
        prompter = ctx.container.force_fetch(LLMTextCompletion)
        for direction in this.data.directions:
            self._driver.parse_command(direction, prompter, message)
        ctx.send_at(this).output(message)
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
        thought = LearningModeThought(args)
        thought.data.max_turns = self._config.max_turns
        return thought

    def result(self, ctx: Context, this: LearningModeThought) -> Optional[Dict]:
        return None

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {
            "process": ProcessCmdReaction(),
        }


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
