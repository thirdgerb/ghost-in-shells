from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ghoshell.ghost.context import Context
    from ghoshell.ghost.uml import UML


class Operator(metaclass=ABCMeta):
    """
    Ghost 运行时的算子
    之所以将逻辑拆成算子, 是为了实现可追溯, 可 debug
    自动暴露思维链条.
    """

    @abstractmethod
    def enqueue(self, ctx: "Context") -> Optional[List["Operator"]]:
        pass

    @abstractmethod
    def run(self, ctx: "Context") -> Optional["Operator"]:
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


class OperationKernel(metaclass=ABCMeta):
    """
    Operators Manager 的实现.
    """

    @abstractmethod
    def record(self, op: Operator) -> None:
        """
        记录一个 op 的信息. 用于 debug.
        """
        pass

    @abstractmethod
    def save_records(self) -> None:
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

    def run_dominos(self, ctx: "Context", initial_op: "Operator") -> None:
        """
        像推倒多米诺骨牌一样, 运行各种算子.
        """
        op = initial_op

        queue: List[Operator] = []
        try:
            count = 0
            while op is not None:
                self.is_stackoverflow(op, count)
                self.record(op)
                count += 1

                # 检查是否要插入队列.
                inserts = op.enqueue(ctx)
                if inserts:
                    queue.append(*inserts)
                    queue.append(op)
                    op = queue[0]
                    queue = queue[1:]
                    continue

                after = op.run(ctx)
                op.destroy()

                if after is not None:
                    op = after
                    continue
                # 入队的出栈.
                if len(queue) > 0:
                    op = queue[0]
                    queue = queue[1:]
                    continue
        # todo: catch
        finally:
            self.save_records()

    @abstractmethod
    def destroy(self) -> None:
        pass


class OperationManager(metaclass=ABCMeta):
    """
    调度工具, 由 Ghost 侧 `主动` 调度上下文状态.
    """

    @abstractmethod
    def go_stage(self, *stages: str) -> "Operator":
        """
        变更状态
        """
        pass

    @abstractmethod
    def redirect_to(self, to: "UML") -> "Operator":
        """
        从当前对话任务, 进入一个目标对话任务.
        """
        pass

    @abstractmethod
    def repeat(self) -> "Operator":
        """
        重复上一轮交互的终点状态.
        """
        pass

    @abstractmethod
    def rewind(self, repeat: bool = False) -> "Operator":
        """
        重置当前对话状态.
        忽略本轮对话内容.
        """
        pass

    @abstractmethod
    def reset(self) -> "Operator":
        """
        清空上下文, 回到起点.
        """
        pass

    @abstractmethod
    def intend_to(self, uml: UML, params: Dict | None = None) -> "Operator":
        pass

    @abstractmethod
    def restart(self) -> "Operator":
        pass

    @abstractmethod
    def wait(self) -> "Operator":
        """
        ghost 上下文同步休眠, 等待下一次 input 的唤醒.
        """
        pass

    @abstractmethod
    def forward(self) -> "Operator":
        """
        如果状态机仍然有栈, 则向前走. 没有的话调用 finish
        """
        pass

    @abstractmethod
    def finish(self) -> "Operator":
        """
        结束当前任务. 相当于 return.
        """
        pass

    @abstractmethod
    def cancel(self, reason: Optional[Any]) -> "Operator":
        """
        取消当前任务.
        """
        pass

    @abstractmethod
    def quit(self, reason: Optional[Any]) -> "Operator":
        """
        退出整个进程.
        """
        pass

    @abstractmethod
    def depend_on(self, target: "UML") -> "Operator":
        """
        依赖一个目标任务
        """
        pass

    @abstractmethod
    def yield_to(self, target: "UML", pid: Optional[str] = None) -> "Operator":
        """
        依赖一个异步任务.
        """
        pass

    @abstractmethod
    def fail(self, reason: Optional[Any]) -> "Operator":
        """
        退出整个进程.
        """
        pass
