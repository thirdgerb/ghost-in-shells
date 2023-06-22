from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, TYPE_CHECKING

from ghoshell.ghost.exceptions import OperatorException

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
        try:
            count = 0
            while op is not None:
                self.is_stackoverflow(op, count)
                self.record(ctx, op)
                count += 1

                # 正式运行.
                # try:
                after = op.run(ctx)
                # except ErrMessageException as e:
                #     ctx.send_at(None).err(e.message, e.CODE, at=e.at)
                #     after = ctx.mind(None).rewind()
                # 检查死循环问题. 每一轮 op 都需要是一个新的 op, 基本要求.
                if after is op:
                    # todo: 写一个好点的 exception
                    raise OperatorException(message="operator loop from %s to %s" % (op, after), at=str(op))

                # 原始 op 销毁.
                op.destroy()
                op = after
        # except OperatorException as e:
        #     raise e
        # except Exception as e:
        #     raise OperatorException(message=str(e), at=str(op), e=e)
        finally:
            self.save_records()

    @abstractmethod
    def destroy(self) -> None:
        pass

#
# class OperationManager(metaclass=ABCMeta):
#     """
#     调度工具, 由 Ghost 侧 `主动` 调度上下文状态.
#     """
#
#     @abstractmethod
#     def go_stage(self, *stages: str) -> "Operator":
#         """
#         往状态机运行栈里插入 stages.
#         注意要避免死循环, 而 Runtime 的实现有责任发现死循环.
#         """
#         pass
#
#     @abstractmethod
#     def redirect_to(self, to: "URL") -> "Operator":
#         """
#         从当前对话任务, 进入一个目标对话任务.
#         如果目标任务和当前任务是同一个 tid, 则意味着问题.
#         """
#         pass
#
#     @abstractmethod
#     def repeat(self) -> "Operator":
#         """
#         重复上一轮交互的终点状态, 触发 OnRepeat 事件.
#         Repeat 不必重复上一轮交互的所有输出, 只需要 Repeat 必要的输出.
#         这个命令对于对话机器人比较有用, 比如机器人向用户询问了一个问题
#         执行 Repeat 就会重复去问用户.
#
#         用 LLM 可以将 Repeat 事件直接告知 LLM, 让它自行重复.
#         """
#         pass
#
#     @abstractmethod
#     def rewind(self, repeat: bool = False) -> "Operator":
#         """
#         重置当前对话状态. 忽视本轮交互的变更.
#         如果执行了 rewind, 理论上不会保存当前交互产生出来的 Process/Task 等变更
#         而是当作什么都没发生过.
#         如果要做更复杂的实现, 就不用 rewind 方法了.
#
#         以前的 commune chatbot 不仅实现了 rewind, 还实现了 process snapshots
#         可以通过 backward 指令返回 n 轮对话之前.
#         这种 rollback 的能力极其复杂, 实际上没有任何办法完美实现.
#         因为在思考运行的过程中, 必然有 IO 已经发生了.
#         """
#         pass
#
#     @abstractmethod
#     def reset(self) -> "Operator":
#         """
#         Reset 的对象是整个会话的 Process, 会清空所有任务回到起点.
#         通常用于兼容一些低水平的异常. 出故障后重置状态
#         对于不可恢复的异常, 也要有一整套恢复办法.
#
#         典型的例子是 task 数据结构变化, 导致记忆回复时会产生 RuntimeException
#         或者 intentions 做了无法向前兼容的改动, 导致 runtime 记忆出错.
#         """
#         pass
#
#     @abstractmethod
#     def intend_to(self, url: URL, params: Dict | None = None) -> "Operator":
#         """
#         Intend to 是中断当前任务, 使之保留在 await_stage 的状态, 然后进入另一个任务.
#         这个过程中可以传递额外的参数, 也就是 params.
#
#         为什么会有两个参数呢?
#         一个是 url.args, 一个是 intention params:
#         - url.args : 系统内部一个任务进入另一个任务的参数, 相当于 class.__init__()  传入的参数或者配置.
#         - intention params : 系统外部输入的信息, 经过结构化解析后沉淀的参数.
#
#         当然对于大模型而言, 只需要有 tokens 就足够了. 但 Task 可以视作对底层能力的编程, 底层能力需要有非常明确的参数抽象.
#         """
#         pass
#
#     @abstractmethod
#     def restart(self) -> "Operator":
#         """
#         重启当前的 Task. 与 go_stage('') 不同, 还会重置掉上下文状态 (重置 thought)
#         """
#         pass
#
#     @abstractmethod
#     def wait(self) -> "Operator":
#         """
#         本来想用 await, 无奈 python 的系统关键字太多, 这是 python 一个巨大的缺点.
#         wait 是挂起整个 Clone. 上下文也会同步休眠, 等待下一次 input 的唤醒.
#
#         而实际上, 当前 Process 进入了 wait 状态, 可能 clone 还不会立刻释放 (unlock), 而是继续去处理异步消息.
#         就看具体怎么实现了.
#         """
#         pass
#
#     @abstractmethod
#     def forward(self) -> "Operator":
#         """
#         如果状态机仍然有栈, 则向前走. 没有的话调用 finish
#         """
#         pass
#
#     @abstractmethod
#     def finish(self) -> "Operator":
#         """
#         结束当前任务.
#         根据 Think.result() 的实现, 会返回一个 result 给依赖当前任务的对象.
#         """
#         pass
#
#     @abstractmethod
#     def cancel(self, reason: Optional[Any] = None) -> "Operator":
#         """
#         取消当前任务.
#         由于存在 depending 建立的回调关系, 取消当前任务, 也会取消它所有的回调任务.
#         """
#         pass
#
#     @abstractmethod
#     def quit(self, reason: Optional[Any] = None) -> "Operator":
#         """
#         退出整个进程.
#         会从 current_task 开始逐个 cancel, 一直 cancel 到 root
#         这也意味着 cancel 的过程中可以中断.
#         """
#         pass
#
#     @abstractmethod
#     def depend_on(self, target: "URL") -> "Operator":
#         """
#         依赖一个目标任务, 目标任务完成后会发起回调.
#         这个目标任务也可能在运行中, depend_on 不会去指定任何 stage.
#         每个 Think 对于别的 Think 而言内部是封闭的.
#         """
#         pass
#
#     @abstractmethod
#     def fail(self, reason: Optional[Any] = None) -> "Operator":
#         """
#         表示当前任务失败, 也会出发和 cancel 一样的回调流程.
#         这里 reason 用什么数据结构, 还没想好. 先瞎糊弄一下.
#         """
#         pass
