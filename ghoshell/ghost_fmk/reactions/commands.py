from abc import ABCMeta, abstractmethod
from typing import List, Dict, Type

from ghoshell.ghost import Reaction, Context, Thought, Operator, Intention, TaskLevel
from ghoshell.ghost_fmk.intentions import Command, CommandOutput, CommandIntention

"""
默认的命令行 reactions.
"""


class CommandReaction(Reaction, metaclass=ABCMeta):
    """
    实现了命令行能力的 Reaction.
    """

    def __init__(self, cmd: Command, level: int = TaskLevel.LEVEL_PRIVATE):
        self._cmd = cmd
        self._level = level

    def level(self) -> int:
        return self._level

    def intentions(self, ctx: Context) -> List[Intention]:
        return [self.command_intention()]

    def command_intention(self) -> CommandIntention:
        return self._cmd.to_intention()

    def react(self, ctx: Context, this: Thought, params: Dict | None) -> Operator | None:
        if params is None:
            ctx.send_at(this).err(f"command {self._cmd.name} got none params")
            return ctx.mind(this).rewind()
        wrapper = self.wrapper()
        output = wrapper(**params)
        return self.on_output(ctx, this, output)

    @classmethod
    def wrapper(cls) -> Type[CommandOutput]:
        return CommandOutput

    @abstractmethod
    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        pass


class HelloWorldCmdReaction(CommandReaction):
    """
    test only reaction
    """

    def __init__(self):
        cmd = Command(
            name="helloworld",
            desc="only for test, print helloworld only",
        )
        super().__init__(cmd, TaskLevel.LEVEL_PUBLIC)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        ctx.send_at(this).text("hello world! from /helloworld command")
        return ctx.mind(this).rewind()
