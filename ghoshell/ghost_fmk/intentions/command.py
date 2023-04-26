from __future__ import annotations

from argparse import ArgumentParser
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field

from ghoshell.ghost import Intention, Context
from ghoshell.ghost_fmk.focus import FocusHandler
from ghoshell.messages import Text

COMMAND_INTENTION = "command_line"


class Argument(BaseModel):
    """
    命令的入参. 详见 CommandConfig.
    由于 pydantic 问题, 必须按顺序定义.
    """
    name: str
    description: str = ""
    short: str = ""
    default: Any = None
    nargs: int | str | None = None
    choices: List[Any] | None = None

    def is_valid(self) -> bool:
        if len(self.name) <= 0:
            return False
        return True


class CommandConfig(BaseModel):
    """
    命令行的配置.
    """
    name: str = ""
    description: str = ""
    epilog: str = ""
    argument: Optional[Argument] = Field(default_factory=lambda: None)
    options: List[Argument] = Field(default_factory=lambda: [])

    def to_intention(self) -> Intention:
        return Intention(KIND=COMMAND_INTENTION, config=self.dict())


class CommandOutput(BaseModel):
    error: bool
    message: str = ""
    params: Dict = {}


class CommandIntention(Intention):
    """
    用来解析命令行的意图
    """
    KIND = COMMAND_INTENTION
    config: CommandConfig
    params: CommandOutput | None = None


class _ArgumentParserWrapper(ArgumentParser):
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
        raise _ExitedException(message)


class _ExitedException(Exception):
    pass


class CommandDriver(FocusHandler):

    def __init__(self, prefix: str):
        self.prefix = prefix[0]
        self.global_commands: Dict[str, CommandIntention] = {}

    def kind(self) -> str:
        return CommandIntention.KIND

    def match(self, ctx: Context, *metas: Intention) -> Optional[Intention]:
        text = ctx.read(Text)
        if text is None:
            return None
        if len(text.content) == 0:
            return None
        command_lines = []
        for meta in metas:
            if isinstance(meta, CommandIntention):
                command_lines.append(meta)
        return self.match_raw_text(text.content, *command_lines)

    def match_raw_text(self, text: str, *metas: CommandIntention) -> Optional[CommandIntention]:
        prefix = text[0]
        if prefix != self.prefix:
            return None

        commands = {}
        for meta in metas:
            if isinstance(meta, CommandIntention):
                commands[meta.config.name] = meta

        line = text[1:]
        seps = line.split(' ', 2)
        name = seps[0]
        if name not in commands:
            return None
        matched_meta = commands[name]
        arguments = "" if len(seps) < 2 else seps[1].strip()
        result = self._parse_command(matched_meta, arguments)
        if result is None:
            return None
        matched = CommandIntention(**matched_meta.dict())
        matched.result = result
        return matched

    def _parse_command(self, command: CommandIntention, arguments: str) -> CommandOutput | None:
        # todo
        config = command.config
        parser = _ArgumentParserWrapper(
            description=config.description,
            epilog=config.epilog,
            add_help=True,
            exit_on_error=True,
        )

        if config.argument is not None:
            argument = config.argument
            fn_args = self.parse_argument_args(argument, False)
            fn_kwargs = self.parse_argument_kwargs(argument)
            parser.add_argument(*fn_args, **fn_kwargs)
        for option in config.options:
            fn_args = self.parse_argument_args(option, True)
            fn_kwargs = self.parse_argument_kwargs(option)
            parser.add_argument(*fn_args, **fn_kwargs)

        # parser.add_argument(
        #     '-h', '--help',
        #     action=_HelperAction,
        #     default=SUPPRESS,
        #     help='show this help message',
        # )

        args = [i for i in filter(lambda i: i, arguments.split(' '))]
        params = {}
        try:
            namespace, _ = parser.parse_known_args(args)
            params = namespace.__dict__
        except _ExitedException as e:
            pass

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
        origin = arg.dict()
        mapping = {
            "dest": "name",
            "description": "help",
            "default": "default",
            "choices": "choices",
            "nargs": "nargs",
            # "type": "type",
        }
        for key in mapping:
            if key not in origin:
                continue
            value = origin[key]
            if value is None:
                continue
            alias = mapping[key]
            result[alias] = value
        return result

    def register_global_intentions(self, *intentions: Intention) -> None:
        for intention in intentions:
            if isinstance(intention, CommandIntention):
                self.global_commands[intention.config.name] = intention

    def wildcard_match(self, ctx: Context) -> Optional[Intention]:
        return self.match(ctx, *self.global_commands.values())
