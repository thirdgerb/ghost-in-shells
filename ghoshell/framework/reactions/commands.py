from abc import ABCMeta, abstractmethod
from typing import List, Dict, Type

from ghoshell.framework.intentions import Command, CommandOutput, CommandIntention
from ghoshell.ghost import Reaction, Context, Thought, Operator, Intention, TaskLevel, CtxTool, URL, RuntimeTool
from ghoshell.utils import InstanceCount

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

    def __init__(
            self,
            name: str = "thought",
            desc: str = "check out current thought",
            level: int = TaskLevel.LEVEL_PUBLIC,
    ):
        cmd = Command(
            name=name,
            desc=desc,
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        """
        todo: 实现 authentication
        """
        thought = CtxTool.fetch_current_thought(ctx)
        ctx.send_at(this).json(thought.model_dump())
        return ctx.mind(this).rewind()


class InstanceCountCmdReaction(CommandReaction):
    """
    检查当前的进程.
    """

    def __init__(
            self,
            name: str = "instance_count",
            desc: str = "count singletons, check out python gc status",
            level: int = TaskLevel.LEVEL_PUBLIC,
    ):
        cmd = Command(
            name=name,
            desc=desc,
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        """
        todo: 实现 authentication
        """
        ctx.send_at(None).json(InstanceCount.count)
        return ctx.mind(None).rewind()


class ProcessCmdReaction(CommandReaction):
    """
    检查当前的进程.
    """

    def __init__(
            self,
            name: str = "process",
            desc: str = "check out current process",
            level: int = TaskLevel.LEVEL_PUBLIC,
    ):
        cmd = Command(
            name=name,
            desc=desc,
            opts=[
                dict(
                    name="brief",
                    short="b",
                    const="true",
                )
            ],
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        """
        todo: 实现 authentication
        """
        process = ctx.runtime.current_process()
        if "brief" in output.params and output.params.get("brief", "") == "true":
            ctx.send_at(None).json(process.brief())
            return ctx.mind(None).rewind()
        else:
            ctx.send_at(None).json(process.model_dump())
            return ctx.mind(None).rewind()


class TaskCmdReaction(CommandReaction):

    def __init__(
            self,
            name: str = "task",
            desc: str = "check out current task data",
            level: int = TaskLevel.LEVEL_PUBLIC,
    ):
        cmd = Command(
            name=name,
            desc=desc,
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        process = ctx.runtime.current_process()
        task = RuntimeTool.fetch_task(ctx, process.current)
        task = ctx.runtime.instance_task(task)
        ctx.send_at(None).json(task.model_dump())
        return ctx.mind(None).rewind()


class QuitCmdReaction(CommandReaction):

    def __init__(
            self,
            name: str = "quit",
            desc: str = "quit current session",
            level: int = TaskLevel.LEVEL_PUBLIC,
    ):
        cmd = Command(
            name=name,
            desc=desc,
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        return ctx.mind(None).quit()


class RestartCmdReaction(CommandReaction):
    """
    重启当前任务.
    """

    def __init__(
            self,
            name: str = "restart",
            desc: str = "restart current task",
            level: int = TaskLevel.LEVEL_PUBLIC,
    ):
        cmd = Command(
            name=name,
            desc=desc,
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        return ctx.mind(None).restart()


class CancelCmdReaction(CommandReaction):

    def __init__(
            self,
            name: str = "cancel",
            desc: str = "cancel current task",
            level: int = TaskLevel.LEVEL_PUBLIC,
    ):
        cmd = Command(
            name=name,
            desc=desc,
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        return ctx.mind(None).cancel()


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
        ctx.send_at(None).text("hello world! from /helloworld command")
        return ctx.mind(None).rewind()


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
            ctx.send_at(None).err("think name must not be empty")
            return ctx.mind(None).rewind()
        if think_name == this.url.think:
            if not stage_name or stage_name == this.url.stage:
                ctx.send_at(None).err(f"think name '{think_name}' is same as current")
                return ctx.mind(None).rewind()
            else:
                # 重定向节点
                return ctx.mind(None).forward(stage_name)
        # 重定向思维.
        return ctx.mind(None).redirect(URL(think=think_name))
