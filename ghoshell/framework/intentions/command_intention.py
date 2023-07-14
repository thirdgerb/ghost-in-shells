from __future__ import annotations

from argparse import ArgumentParser
from typing import Dict, List, Any, Optional, ClassVar

from pydantic import BaseModel, Field

from ghoshell.ghost import Intention, Context, FocusDriver
from ghoshell.ghost import Operator, CtxTool
from ghoshell.messages import Text

CommandIntentionKind = "command_line"


class Argument(BaseModel):
    """
    命令的入参. 详见 CommandConfig.
    由于 pydantic 问题, 必须按顺序定义.
    """
    name: str
    desc: str = ""
    short: str = ""
    default: Any = None
    const: str | None = None
    nargs: int | str | None = None
    choices: List[Any] | None = None

    def is_valid(self) -> bool:
        if len(self.name) <= 0:
            return False
        return True


class Command(BaseModel):
    """
    命令行的配置.
    """
    name: str = ""
    desc: str = ""
    arg: Optional[Argument] = Field(default_factory=lambda: None)
    opts: List[Argument] = Field(default_factory=lambda: [])
    epilog: str = ""

    def to_intention(self) -> CommandIntention:
        return CommandIntention(kind=CommandIntentionKind, config=self.model_dump())


class CommandOutput(BaseModel):
    """
    命令行输出的封装.
    """
    error: bool
    message: str = ""
    params: Dict[str, Any] = {}


class CommandIntention(Intention):
    """
    用来解析命令行的意图
    用 Command.to_intention 来生成.
    """
    kind: str = CommandIntentionKind
    config: Command
    params: CommandOutput | None = None

    def action(self, ctx: Context) -> Operator | None:
        if self.params is not None:
            if self.params.error:
                ctx.send_at(None).err(self.params.message)
                return ctx.mind(None).rewind()
            elif self.params.message != "":
                ctx.send_at(None).text(self.params.message)
                return ctx.mind(None).rewind()
        return None


class _ArgumentParserWrapper(ArgumentParser):
    """
    对 argparse 库的兼容.
    """
    error_occur: bool = False
    message: str = ""

    def error(self, message: str) -> None:
        self.error_occur = True
        self.exit(message=message)

    def print_help(self, file=None):
        self.message = self.format_help()

    def exit(self, status=0, message=None):
        if message:
            self.message = message
        pass


class HelpCommand(CommandIntention):
    config: Command = Command(
        name="help",
        desc="show all the available commands",
    )

    def action(self, ctx: Context) -> Operator | None:
        i = super().action(ctx)
        if i is not None:
            return i

        handler = ctx.container.get(CommandFocusDriver)
        if handler is None:
            ctx.send_at(None).text("unknown command")
            return ctx.mind(None).rewind()

        grouped_intentions = CtxTool.context_intentions(ctx)
        command_intentions = grouped_intentions.get(CommandIntentionKind, [])
        commands: List[Command] = [self.config]
        for intention in command_intentions:
            cmd = CommandIntention(**intention.model_dump())
            commands.append(cmd.config)
        # 进行解析.
        format_line = handler.format_help_commands(commands)
        ctx.send_at(None).text(format_line, markdown=True)
        return ctx.mind(None).rewind()


class CommandFocusDriver(FocusDriver):
    # 命令的前缀号
    prefix: ClassVar[str] = "/"

    def __init__(self, default_commands: List[CommandIntention] | None = None):
        self.global_commands: Dict[str, CommandIntention] = {}
        if default_commands is None:
            default_commands = [
                HelpCommand()
            ]
        self.default_commands: List[CommandIntention] = default_commands

    def kind(self) -> str:
        return CommandIntentionKind

    @classmethod
    def format_help_commands(cls, commands: List[Command]) -> str:
        head = f"""
show current commands. use -h option on command to see details:

"""
        body_lines = [head]
        for cmd in commands:
            body_lines.append(f"- {cls.prefix}{cmd.name}: {cmd.desc}")
        return "\n".join(body_lines)

    def match(self, ctx: Context, *metas: Intention) -> Optional[Intention]:
        text = ctx.read(Text)
        if text is None:
            return None
        if len(text.content) == 0:
            return None
        command_lines = self.default_commands.copy()
        for meta in metas:
            if isinstance(meta, CommandIntention):
                command_lines.append(meta)
            else:
                # 二次包装.
                line = CommandIntention(**meta.model_dump())
                command_lines.append(line)
        return self.match_raw_text(text.content, *command_lines)

    def match_raw_text(self, text: str, *metas: CommandIntention) -> Optional[CommandIntention]:
        """
        匹配单个命令.
        """
        prefix = text[0]
        if prefix != self.prefix:
            return None

        commands = {}
        for meta in metas:
            if isinstance(meta, CommandIntention):
                # 顺序优先, 后面的命令覆盖前面的命令.
                commands[meta.config.name] = meta

        command_line = text[len(self.prefix):]
        seps = command_line.split(' ', 2)
        command_name = seps[0]
        if command_name not in commands:
            return None
        matched_meta = commands[command_name]
        arguments = "" if len(seps) < 2 else seps[1].strip()
        result = self._parse_command(matched_meta, arguments)
        if result is None:
            return None
        matched = matched_meta.copy()
        matched.params = result
        return matched

    def _parse_command(self, command: CommandIntention, arguments: str) -> CommandOutput | None:
        # todo
        config = command.config
        parser = _ArgumentParserWrapper(
            description=config.desc,
            epilog=config.epilog,
            add_help=True,
            exit_on_error=False,
        )
        parser.prog = command.config.name

        if config.arg is not None:
            argument = config.arg
            fn_args = self.parse_argument_args(argument, False)
            fn_kwargs = self.parse_argument_kwargs(argument)
            parser.add_argument(*fn_args, **fn_kwargs)
        for option in config.opts:
            fn_args = self.parse_argument_args(option, True)
            fn_kwargs = self.parse_argument_kwargs(option)
            parser.add_argument(*fn_args, **fn_kwargs)

        args = [i for i in filter(lambda i: i, arguments.split(' '))]
        namespace, _ = parser.parse_known_args(args)
        params = namespace.__dict__

        result = CommandOutput(
            error=parser.error_occur,
            message=parser.message,
            params=params,
        )
        return result

    @classmethod
    def parse_argument_args(cls, arg: Argument, is_option: bool) -> List:
        result = []
        if is_option:
            if len(arg.short) > 0:
                short = arg.short[0]
                result.append(f"-{short}")
                result.append(f"--{arg.name}")
        else:
            result.append(arg.name)
        return result

    @classmethod
    def parse_argument_kwargs(cls, arg: Argument) -> Dict:
        result = {}
        origin = arg.model_dump()
        mapping = {
            "dest": "name",
            "description": "help",
            "default": "default",
            "choices": "choices",
            "nargs": "nargs",
            "const": "const",
            "type": "type",
        }
        for key in mapping:
            if key not in origin:
                continue
            value = origin[key]
            if value is None:
                continue
            alias = mapping[key]
            result[alias] = value
        if "const" in result:
            result["nargs"] = "?"
        return result

    def register_global_intentions(self, *intentions: Intention) -> None:
        for intention in intentions:
            if isinstance(intention, CommandIntention):
                self.global_commands[intention.config.name] = intention

    def wildcard_match(self, ctx: Context) -> Optional[Intention]:
        return self.match(ctx, *self.global_commands.values())
