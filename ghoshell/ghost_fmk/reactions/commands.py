from abc import ABCMeta, abstractmethod
from typing import List, Dict, Type

from ghoshell.ghost import Reaction, Context, Thought, Operator, Intention, TaskLevel, CtxTool, URL
from ghoshell.ghost_fmk.intentions import Command, CommandOutput, CommandIntention, CommandIntentionKind
from ghoshell.ghost_fmk.intentions import FocusOnCommandHandler

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
        if output.message:
            if output.error:
                ctx.send_at(this).err(output.message)
            else:
                ctx.send_at(this).text(output.message)
            return ctx.mind(this).rewind()
        return self.on_output(ctx, this, output)

    @classmethod
    def wrapper(cls) -> Type[CommandOutput]:
        return CommandOutput

    @abstractmethod
    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        pass


class ThoughtCmdReaction(CommandReaction):
    """
    查看 Thought 的 reaction
    """

    def __init__(self, level: int = TaskLevel.LEVEL_PUBLIC):
        cmd = Command(
            name="thought",
            desc="check out current thought",
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        """
        todo: 实现 authentication
        """
        ctx.send_at(this).json(this.dict())
        return ctx.mind(this).rewind()


class ProcessCmdReaction(CommandReaction):
    """
    检查当前的进程.
    """

    def __init__(self, level: int = TaskLevel.LEVEL_PUBLIC):
        cmd = Command(
            name="process",
            desc="check out current process",
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        """
        todo: 实现 authentication
        """
        process_data = ctx.runtime.current_process().dict()
        ctx.send_at(this).json(process_data)
        return ctx.mind(this).rewind()


class HelpCmdReaction(CommandReaction):
    """
    help: 查看可行的命令.
    """

    def __init__(self, level: int = TaskLevel.LEVEL_PUBLIC):
        cmd = Command(
            name="help",
            desc="check out all available commands",
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        """
        todo: 实现 authentication
        """
        handler = ctx.container.get(FocusOnCommandHandler)
        if handler is None:
            ctx.send_at(this).text("unknown command")
            return ctx.mind(this).rewind()

        grouped_intentions = CtxTool.context_intentions(ctx)
        command_intentions = grouped_intentions.get(CommandIntentionKind, [])
        commands: List[Command] = []
        for intention in command_intentions:
            cmd = CommandIntention(**intention.dict())
            commands.append(cmd.config)
        # 进行解析.
        format_line = handler.format_help_commands(commands)
        ctx.send_at(this).text(format_line, markdown=True)
        return ctx.mind(this).rewind()


class HelloWorldCmdReaction(CommandReaction):
    """
    test only reaction
    """

    def __init__(self, level: int = TaskLevel.LEVEL_PUBLIC):
        cmd = Command(
            name="helloworld",
            desc="only for test, print helloworld only",
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        ctx.send_at(this).text("hello world! from /helloworld command")
        return ctx.mind(this).rewind()


class RedirectCmdReaction(CommandReaction):
    """
    手动重定向
    """

    def __init__(self, level: int = TaskLevel.LEVEL_PUBLIC):
        cmd = Command(
            name="redirect",
            desc="only for test, print helloworld only",
            arg=dict(
                name="think_name",
                desc="value is mindset think name"
            ),
            opts=[
                dict(
                    name="stage_name",
                    desc="value is stage name",
                    short="s",
                    default="",
                ),
            ],
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        think_name = output.params.get("think_name", None)
        stage_name = output.params.get("stage_name", "")
        if not think_name:
            ctx.send_at(this).err("think name must not be empty")
            return ctx.mind(this).rewind()
        if think_name == this.url.resolver:
            if not stage_name or stage_name == this.url.stage:
                ctx.send_at(this).err(f"think name '{think_name}' is same as current")
                return ctx.mind(this).rewind()
            else:
                # 重定向节点
                return ctx.mind(this).forward(stage_name)
        # 重定向思维.
        return ctx.mind(this).redirect(URL(resolver=think_name))
