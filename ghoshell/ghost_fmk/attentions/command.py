from argparse import ArgumentParser
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field

from ghoshell.ghost import Intention, Context
from ghoshell.ghost_fmk.attentions.attentions import AttentionDriver


class Argument(BaseModel):
    name: str = ""
    short: str = ""
    description: str = ""
    default: Any = None
    nargs: int | str | None = None
    choices: List[Any] | None = None
    type: Any | None = None

    def is_valid(self) -> bool:
        if len(self.name) <= 0:
            return False
        return True


class CommandConfig(BaseModel):
    name: str = ""
    description: str = ""
    epilog: str = ""
    argument: Argument | None = None
    options: List[Argument] = Field(default_factory=lambda: [])


class CommandOutput(BaseModel):
    error: bool
    message: str = ""
    params: Dict = {}


class CommandLine(Intention):
    KIND = "command_line"
    config: CommandConfig
    matched: CommandOutput | None = None


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


class CommandDriver(AttentionDriver):

    def __init__(self, prefix: str):
        self.prefix = prefix[0]
        self.global_commands: Dict[str, CommandLine] = {}

    def kind(self) -> str:
        return CommandLine.KIND

    def match(self, ctx: Context, *metas: Intention) -> Optional[Intention]:
        text = ctx.input.payload.text
        if text is None:
            return None
        if len(text.raw) == 0:
            return None
        command_lines = []
        for meta in metas:
            if isinstance(meta, CommandLine):
                command_lines.append(meta)
        return self.match_raw_text(text.raw, *command_lines)

    def match_raw_text(self, text: str, *metas: CommandLine) -> Optional[CommandLine]:
        prefix = text[0]
        if prefix != self.prefix:
            return None

        commands = {}
        for meta in metas:
            if isinstance(meta, CommandLine):
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
        matched = CommandLine(**matched_meta.dict())
        matched.result = result
        return matched

    def _parse_command(self, command: CommandLine, arguments: str) -> CommandOutput | None:
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
        return result

    def register(self, *intentions: Intention) -> None:
        for intention in intentions:
            if isinstance(intention, CommandLine):
                self.global_commands[intention.config.name] = intention

    def wildcard_match(self, ctx: Context) -> Optional[Intention]:
        return self.match(ctx, *self.global_commands.values())
