from abc import ABCMeta, abstractmethod
from typing import Optional, List

from ghoshell.ghost.context import Context
from ghoshell.ghost.operator import Operator
from ghoshell.ghost.runtime import TaskStatus
from ghoshell.ghost.tool import RuntimeTool, CtxTool
from ghoshell.ghost.url import URL
from ghoshell.messages import Tasked


class AbsOperator(Operator, metaclass=ABCMeta):
    """
    operator 基类. 没有提供有用的方法, 只是提供一个开发范式
    方便开发者建立思路, 划分边界.
    """

    def run(self, ctx: "Context") -> Optional["Operator"]:
        """
        用一个标准流程来约定 Operator 的开发方式.
        """
        # 先看是否有拦截发生, 如果发生了拦截, 则 operator 不会真正执行.
        interceptor = self._intercept(ctx)
        if interceptor is not None:
            return interceptor
        # 运行 operator 的事件.
        result_op = self._run_operation(ctx)
        if result_op is not None:
            return result_op
        # 如果运行事件没结果, 就往后走.
        return self._fallback(ctx)

    @abstractmethod
    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        """
        判断是否有拦截事件, 可以组织 operator 运行
        """
        pass

    @abstractmethod
    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        """
        触发 Operator 自身的事件.
        """
        pass

    @abstractmethod
    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        """
        如果没有任何中断, 则继续往后运行.
        """
        pass


class ChainOperator(Operator):
    """
    链式 operator
    """

    def __init__(self, chain: List[Operator]):
        self.chain = chain

    def run(self, ctx: "Context") -> Optional["Operator"]:
        chain = self.chain
        if len(chain) == 0:
            return None
        op = chain[0]
        chain = chain[1:]
        after = op.run(ctx)
        if after is None:
            return ChainOperator(chain)
        if len(chain) == 0:
            return after
        return ChainOperator([after] + chain)

    def destroy(self) -> None:
        del self.chain


class ReceiveInputOperator(AbsOperator):
    """
    接受到一个 Input
    """

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        process = ctx.clone.runtime.current_process()
        # root 如果没有初始化.
        tasked = ctx.read(Tasked)
        if not process.root:
            if tasked is not None:
                root = RuntimeTool.new_task(
                    ctx,
                    URL.new(resolver=tasked.resolver, stage="", args=tasked.args),
                )
            else:
                # 否则 root 用默认方式生成.
                root = RuntimeTool.new_task(ctx, ctx.clone.root)
            RuntimeTool.store_task(ctx, root)
            # 保存变更. 这一步理论上不是必须的.
            ctx.clone.runtime.store_process(process)

        if tasked is not None:
            # tasked 的情况, 只需要执行 tasked 的任务就可以了.
            return self._handle_tasked(ctx, tasked)

        # 正常情况下, 要判断是不是 new
        if process.is_new:
            # 保证不再是 new 了.
            process.add_round()
            ctx.clone.runtime.store_process(process)
            root_task = RuntimeTool.fetch_root_task(ctx)
            # 必须先激活根节点, 然后让它进入某个状态后, 开始 receive input.
            # todo: 激活的过程是否要
            return ChainOperator([ActivateOperator(root_task.url), self])
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:

        # 如果 payload tid 存在, 则消息希望命中目标任务. 需要调整任务的优先顺序.
        self._check_payload_tid(ctx)

        # 接下来进行意图匹配.
        return self._match_input_reactions(ctx)

    @classmethod
    def _match_input_reactions(cls, ctx: Context) -> Optional[Operator]:

        CtxTool.context_attentions()

    @classmethod
    def _check_payload_tid(cls, ctx: Context) -> None:
        """
        如果 payload.tid 存在, 调整任务的优先顺序.
        """
        payload = ctx.input.payload
        if not payload.tid:
            return
        target_task = RuntimeTool.fetch_task(ctx, payload.tid)
        if target_task is None:
            return
        if target_task.status != TaskStatus.WAITING:
            return
        process = ctx.clone.runtime.current_process()
        process.await_at(target_task.tid)
        ctx.clone.runtime.store_process(process)
        return

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return FallbackOperator()

    @classmethod
    def _payload_tid_op(cls, ctx: Context, payload: Payload, enqueue: List[Operator]) -> List[Operator]:
        """
        如果 payload 里包含了 tid, 说明消息有明确的目标任务.
        系统先要重定向到这个任务, 然后再用它接受信息.
        """
        if not payload.tid:
            return enqueue
        # 如果 payload 包含了 tid, 意味着它应该命中某个任务.
        payload_target_task = RuntimeTool.fetch_task(ctx, payload.tid)

        # 检查目标任务是否存在.
        if payload_target_task is None:
            return enqueue

        process = ctx.clone.runtime.current_process()
        # 如果目标任务就是 current task, 则
        if payload_target_task.tid == process.awaiting_task:
            return enqueue
        # 如果 payload 对应的任务不在等待状态?
        if payload_target_task.status != TaskStatus.WAITING:
            return enqueue
        enqueue.append(OpAwait(payload_target_task))
        return enqueue

    @classmethod
    def _handle_tasked(cls, ctx: Context, tasked: Tasked) -> Optional[Operator]:
        task = RuntimeTool.fetch_task(ctx, tasked.tid)
        if task is None:
            task = RuntimeTool.new_task(ctx, URL(think=tasked.resolver, stage=tasked.stage, args=tasked.args.copy()))
        task.merge_tasked(tasked)
        RuntimeTool.store_task(ctx, task)
        match tasked.status:
            case TaskStatus.WAITING:
                return OpAwait(task.url)
            case TaskStatus.CANCELED:
                return OpCancel(task.url, None, None)
            case TaskStatus.FAILED:
                return OpFail(task.url, None, None)
            case TaskStatus.PREEMPTING:
                return OpBlock(task.url, None)
            case TaskStatus.FINISHED:
                return OpFinish(task.url, task.tid)
            case _:
                return OpActivate(task.url, None)

    def destroy(self) -> None:
        return


class ActivateOperator(AbsOperator):

    def __init__(self, url: URL):
        self.url = url
