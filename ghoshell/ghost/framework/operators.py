from typing import Optional

from ghoshell.ghost import Operator, Context, Thought, UML, Task


# class AbsOperator(IOperator, metaclass=ABCMeta):

class Fallback(Operator):
    pass


class RedirectTo(Operator):
    """
    从一个任务, 跳转到另一个任务.
    """
    fr: Thought
    to: UML

    def __init__(self, fr: Thought, to: UML):
        self.fr = fr
        self.to = to

    @property
    def current(self) -> UML:
        return self.fr.uml

    def forward(self, ctx: "Context") -> Optional[Operator]:
        # 将当前节点状态结算, 然后加入 blocking 队列
        # 执行目标节点的 on_start 方法.
        target_task = ctx.task(self.to)
        if target_task.is_blocking:
            pass
        elif target_task.is_finished:
            pass
        elif target_task.is_yielding:
            pass
        elif target_task.is_depending:
            pass
        elif target_task.is_await:
            pass
        elif target_task.is_canceled:
            pass

    def destroy(self) -> None:
        del self.fr
        del self.to


class Activate(Operator):
    """

    """

    def __init__(self, task: Task):
        self.task: Task = task

    @property
    def current(self) -> UML:
        return self.task.uml

    def forward(self, ctx: "Context") -> Optional[Operator]:
        # 根据 task 的状态, 决定怎么 run.
        # - finished: 返回
        # - canceled: 返回
        # - blocking: 执行
        # - yielding: 提示继续 yielding, 支持一个 peek 事件.
        # -
        pass

    def destroy(self) -> None:
        pass


class DependOn(Operator):
    """
    当前任务依赖另一个任务
    """

    # 来自的任务
    fr: Thought
    # 依赖的任务
    to: UML

    def __init__(self, current: Thought, depending: UML):
        self.fr = current
        self.to = depending

    @property
    def current(self) -> UML:
        # current 成为了被依赖的任务.
        return self.to

    def forward(self, ctx: Context) -> Optional[Operator]:
        target_task = ctx.task(self.to)
        from_task = ctx.task(self.current)
        from_task.depending = target_task.tid
        target_task.depended_by.add(from_task.tid)

        process = ctx.runtime.current_process()
        process.depending.add(from_task.tid)

        # 启动目标任务.
        return Activate(target_task)

    def destroy(self) -> None:
        del self.to
        del self.fr


class Finish(Operator):
    """
    当前任务结束
    """

    def __init__(self, this: Thought):
        self.this: Thought = this

    def forward(self, ctx: Context) -> Optional[Operator]:
        pass


class Cancel(Operator):
    """
    取消当前对话.
    """
    pass


class IntendTo(Operator):
    pass


class Quit(Operator):
    """
    退出所有的对话.
    """
    pass


class Fail(Operator):
    pass


class Retain(Operator):
    pass


class Callback(Operator):
    pass
