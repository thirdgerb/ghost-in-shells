from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ghoshell.ghost.context import Context
from ghoshell.ghost.uml import UML


class Operator(metaclass=ABCMeta):
    """
    Ghost 运行时的算子
    """

    @staticmethod
    def fire(ctx: Context, e: Event) -> Optional[Operator]:
        """
        触发一个 stage 可以理解的事件.
        """
        think = ctx.mind.fetch(e.current.think)
        # stage 的实例化.
        current_stage = e.current.stage
        if current_stage:
            stage = think.all_stages().get(e.current.stage)
        else:
            stage = think.default_stage()

        if stage is None:
            # todo: 实现 exception
            raise Exception()
        this = think.thought(ctx, e.current.args)
        task = ctx.task(e.current)
        # 进行对象化的封装.
        this.from_task(task)
        # 出发 operator 事件
        return stage.on_event(this, ctx, e)

    @abstractmethod
    def forward(self, ctx: "Context") -> Optional[Operator]:
        """
        继续下一个任务.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        方便 python 回收垃圾
        """
        pass


class Event(metaclass=ABCMeta):
    @property
    @abstractmethod
    def current(self) -> UML:
        pass


class Operation(metaclass=ABCMeta):
    """
    调度工具, 由 Ghost 侧 `主动` 调度上下文状态.
    """

    @abstractmethod
    def go_stage(self, *stages: str) -> Operator:
        """
        变更状态
        """
        pass

    def redirect_to(self, to: UML, blocking: bool = True) -> Operator:
        """
        从当前对话任务, 进入一个目标对话任务.
        """
        pass

    @abstractmethod
    def repeat(self) -> Operator:
        """
        回到上一轮交互的终点状态.
        """
        pass

    @abstractmethod
    def restart(self) -> Operator:
        """
        当前任务回到起点.
        """
        pass

    @abstractmethod
    def rewind(self) -> Operator:
        """
        重置本轮交互所有的状态变更.(其实就是不保存)
        """
        pass

    @abstractmethod
    def sleep(self) -> Operator:
        """
        ghost 上下文同步休眠, 等待下一次 input 的唤醒.
        """
        pass

    @abstractmethod
    def forward(self, *stages: str) -> Operator:
        """
        如果状态机仍然有栈, 则向前走. 没有的话调用 finish
        """
        pass

    @abstractmethod
    def finish(self) -> Operator:
        """
        结束当前任务. 相当于 return.
        """
        pass

    @abstractmethod
    def cancel(self, reason: Optional[Any]) -> Operator:
        """
        取消当前任务.
        """
        pass

    @abstractmethod
    def quit(self, reason: Optional[Any]) -> Operator:
        """
        退出整个进程.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass


class OperatorManager(metaclass=ABCMeta):
    """
    Operators Manager 的实现.
    """

    @abstractmethod
    def trace(self, op: Operator) -> None:
        """
        记录一个 op 的信息. 用于 debug.
        """
        pass

    @abstractmethod
    def save_trace(self) -> None:
        """
        将运行轨迹保存下来, 用于 debug.
        里面的逻辑可以自定义, 比如 debug 模式才去 save.
        """
        pass

    @abstractmethod
    def is_stackoverflow(self, op: Operator, length: int) -> bool:
        """
        判断当前逻辑是否是 stack overflow, 或者无限循环, 或者计算轮次超过上限.
        stack overflow 还有另一种处理机制, 在 processor 运转过程中判断 tasks 的上限
        task 链条成环是一种常见的可能性.
        """
        pass

    def run_dominos(self, ctx: Context, initial_op: Operator) -> None:
        """
        像推倒多米诺骨牌一样, 运行各种算子.
        """
        op = initial_op
        try:
            count = 0
            while op is not None:
                self.is_stackoverflow(op, count)
                self.trace(op)
                count += 1
                intercepted = op.intercept(ctx)
                if intercepted is not None and intercepted is not op:
                    op.destroy()
                    op = intercepted
                    continue
                after = op.forward(ctx)
                op.destroy()
                op = after
        # todo: catch
        finally:
            self.save_trace()

    @abstractmethod
    def destroy(self) -> None:
        pass
