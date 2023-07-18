from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, TYPE_CHECKING

from ghoshell.ghost.error import OperatorError, ForbiddenError, ThinkError, CloneError

if TYPE_CHECKING:
    from ghoshell.ghost.context import Context


class Operator(metaclass=ABCMeta):
    """
    Ghost 运行时 (runtime) 的算子
    之所以将逻辑拆成算子, 是为了实现可追溯, 可 debug
    自动暴露思维链条.
    """

    @abstractmethod
    def run(self, ctx: "Context") -> Optional["Operator"]:
        """
        运行当前算子, 并给出下一个算子.
        如果为 None, 表示计算流程已经结束.
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
    def record(self, ctx: "Context", op: Operator) -> None:
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

    @abstractmethod
    def init_operator(self) -> "Operator":
        pass

    def run_dominos(self, ctx: "Context", initial_op: "Operator") -> None:
        """
        像推倒多米诺骨牌一样, 运行各种算子.
        """
        op = initial_op
        err_times = 0
        try:
            count = 0
            while op is not None:
                self.is_stackoverflow(op, count)
                self.record(ctx, op)
                count += 1

                if err_times > 2:
                    raise CloneError(f"operation cycle error occur times {err_times}")

                # 正式运行.
                # try:
                try:
                    after = op.run(ctx)

                except ForbiddenError as e:
                    err_times += 1
                    ctx.send_at(None).text(e.message)
                    after = ctx.mind(None).rewind()

                except ThinkError as e:
                    err_times += 1

                    ctx.send_at(None).text(e.message)
                    ctx.send_at(None).err(e.message, e.CODE)
                    after = ctx.mind(None).rewind()

                # 检查死循环问题. 每一轮 op 都需要是一个新的 op, 基本要求.
                if after is op:
                    # todo: 写一个好点的 exception
                    raise OperatorError(message="operator loop from %s to %s at %s" % (op, after, str(op)))

                # 原始 op 销毁.
                op.destroy()
                op = after

        finally:
            self.save_records()

    @abstractmethod
    def destroy(self) -> None:
        pass
