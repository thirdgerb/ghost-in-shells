from abc import ABCMeta, abstractmethod
from typing import Optional, Dict, List, Any, Tuple, Type

from ghoshell.ghost import Callback
from ghoshell.ghost import Context, URL, Process
from ghoshell.ghost import Fallback, Intending, Attending
from ghoshell.ghost import OnPreempt
from ghoshell.ghost import OnStart, OnStaging
from ghoshell.ghost import Operator, OperationManager
from ghoshell.ghost import Payload
from ghoshell.ghost import RuntimeTool, CtxTool
from ghoshell.ghost import Task, TaskStatus, TaskLevel
from ghoshell.ghost import Thought
from ghoshell.ghost import UnhandledException, RuntimeException
from ghoshell.ghost import Withdrawing, Canceling, Failing, Quiting
from ghoshell.messages import Tasked


class AbsOperator(Operator, metaclass=ABCMeta):

    def run(self, ctx: "Context") -> Optional["Operator"]:
        # 先看是否有拦截发生, 如果发生了拦截, 则 operator 不会真正执行.
        interceptor = self._intercept(ctx)
        if interceptor is not None:
            return interceptor
        # 运行 operator 的事件.
        event_op = self._run_operation(ctx)
        if event_op is not None:
            return event_op
        # 如果运行事件没结果, 就往后走.
        return self._next(ctx)

    def prepose(self, ctx: "Context") -> List["Operator"] | None:
        """
        是否有前置节点.
        FIFO, 头部在数组 index = 0
        """
        return None

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
    def _next(self, ctx: "Context") -> Optional["Operator"]:
        """
        如果没有任何中断, 则继续往后运行.
        """
        pass


class OpReceive(AbsOperator):

    def __init__(self):
        self.enqueued = False

    def prepose(self, ctx: "Context") -> Optional[List["Operator"]]:
        if self.enqueued:
            return None
        self.enqueued = True

        # 前置准备.
        enqueue: List[Operator] = []
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        enqueue = self._init_new_process(ctx, process, enqueue)
        enqueue = self._payload_tid_op(ctx, payload=ctx.input.payload, enqueue=enqueue)
        return enqueue

    @classmethod
    def _init_new_process(cls, ctx: Context, process: Process, enqueue: List[Operator]) -> List[Operator]:
        if not process.is_new:
            return enqueue
        # 保证 process 不是 new 了.
        process.round += 1
        root = process.root_task
        # root 如果没有初始化.
        if root:
            return enqueue
        tasked = ctx.read(Tasked)
        # 先用
        if tasked is not None:
            root = RuntimeTool.new_task(
                ctx,
                URL.new(resolver=tasked.resolver, stage=tasked.stage, args=tasked.args),
            )
            RuntimeTool.store_task(ctx, root)
            # tasked 的情况, 不需要重新启动.
            # 等待下一轮处理
            return enqueue
        # 否则 root 用默认方式生成.
        root = RuntimeTool.new_task(ctx, ctx.clone.root)
        RuntimeTool.store_task(ctx, root)
        # 意思意思保存下.
        ctx.clone.runtime.store_process(process)
        # 让 process 变成 not new
        # 先要启动.
        enqueue.append(OpActivate(root, None))
        return enqueue

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

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:

        # 如果消息是 tasked, 则直接定向到目标任务.
        tasked = ctx.read(Tasked)
        if tasked is not None:
            return self._handle_tasked(ctx, tasked)

        #  接下来进行意图匹配
        awaiting_task = ctx.clone.runtime.current_process().awaiting_task
        # 检查是否匹配到某个 router
        router_intentions = CtxTool.context_forward_intentions(ctx)
        matched = CtxTool.match_intentions(ctx, router_intentions, awaiting_task.level == TaskLevel.LEVEL_PUBLIC)
        if matched is not None:
            return OpIntendTo(matched.fr, matched.matched, route=True)

        # 检查是否匹配了回调栈中的意图.
        fallback_intentions = CtxTool.context_backward_intentions(ctx)
        matched = CtxTool.match_intentions(ctx, fallback_intentions, public=False)
        if matched is not None:
            return OpIntendTo(matched.fr, matched.matched, route=False)
        return None

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
            case TaskStatus.CANCELING:
                return OpCancel(task.url, None, None)
            case TaskStatus.FAILING:
                return OpFail(task.url, None, None)
            case TaskStatus.PREEMPTING:
                return OpBlock(task.url, None)
            case TaskStatus.FINISHED:
                return OpFinish(task.url, task.tid)
            case _:
                return OpActivate(task.url, None)

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        pass

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return OpFallback()

    def destroy(self) -> None:
        del self.enqueued


class OpFallback(AbsOperator):
    """
    没有任何意图被匹配到时.
    会进入到 fallback 流程, 返回
    """

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        process = ctx.clone.runtime.current_process()
        #  让 current 对话任务来做兜底
        forward = self.fallback_to_task(ctx, process.awaiting_task)
        if forward is not None:
            return forward
        # 让 root 级别的对话任务来做兜底.
        forward = self.fallback_to_task(ctx, process.root_task)
        if forward is not None:
            return forward
        return None

    def _next(self, ctx: "Context") -> Optional[Operator]:
        # 无法处理的输入消息, 返回错误.
        # todo: fulfill exception details
        raise UnhandledException("todo")

    @classmethod
    def fallback_to_task(cls, ctx: "Context", task: Task) -> Optional[Operator]:
        # 当前任务.  fallback
        event = Fallback(task, None, None)
        return RuntimeTool.fire_event(ctx, event)

    def destroy(self) -> None:
        pass


class OpIntendTo(AbsOperator):
    """
    命中了一个意图, 前往目标 Task
    过程中生产一个事件, 如果没问题的话就正式激活目标任务.
    """

    def __init__(
            self,
            to: URL,
            params: Optional[Dict] = None,
            fr: URL | None = None,
            route: bool = False,
    ):
        # 匹配的目标
        self.to: URL = to
        # 匹配的参数, 如果为 none 的话还需要二次检查.
        self.fr = fr
        self.params: Optional[Dict] = params
        self.attend = route

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        # target_task = RuntimeTool.fetch_task_by_url(ctx, self.to, True)
        # # 只有 waiting 状态, 才需要专门 preempt 一下.
        # # todo: 验证这个思路是否正确. 目前的 Operator 流程还是不流畅.
        # if target_task.status != TaskStatus.WAITING:
        #     return None
        #
        # fr = None
        # if self.fr is not None:
        #     fr = RuntimeTool.fetch_task_by_url(ctx, self.to, False)
        # event = OnPreempt(target_task, fr)
        # # 为 None 的话就继续往后走.
        # return RuntimeTool.fire_event(ctx, event)

        # 去掉了复杂逻辑, 先从最简单的来. 以后再想复杂的流程.
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        params = self.params
        # 尽量携带参数来访问.
        if params is None:
            stage = CtxTool.force_fetch_stage(ctx, self.to.resolver, self.to.resolver)
            intentions = stage.intentions(ctx)
            if intentions is not None:
                matched = ctx.clone.attentions.match(ctx, *intentions)
                params = matched.matched

        wrapper: Type[Intending] = Attending if self.attend else Intending
        task = RuntimeTool.fetch_task_by_url(ctx, self.to, True)
        event = wrapper(task, self.fr, params)
        return RuntimeTool.fire_event(ctx, event)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.params
        del self.fr
        del self.to
        del self.attend


class OpGoStage(AbsOperator):
    """
    当前任务切换一个 stage.
    """

    def __init__(self, url: URL, tid: str, *stages: str):
        self.url = url
        self.tid = tid
        self.forwards: Tuple = stages

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        task = RuntimeTool.fetch_task(ctx, self.tid)
        # 将 stages 插入到前面.
        if len(self.forwards) > 0:
            task.insert(*self.forwards)

        # 离开时保存.
        RuntimeTool.store_task(ctx, task)
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        task = RuntimeTool.fetch_task(ctx, self.tid)
        success = task.forward()
        # forward 到头了, 就进入 finish 进程.
        if not success:
            # 走 finish 流程.
            return OpFinish(self.url, self.tid)

        # 否则运行当前节点.
        RuntimeTool.store_task(ctx, task)

        # 触发事件.
        event = OnStaging(task, None)
        return RuntimeTool.fire_event(ctx, event)

    def destroy(self) -> None:
        del self.url
        del self.tid
        del self.forwards


class OpActivate(AbsOperator):

    def __init__(self, target: URL, fr: URL | None):
        self.target = target
        self.fr = fr

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        task = RuntimeTool.fetch_task_by_url(ctx, self.target, True)
        fr = None
        if self.fr is not None:
            fr = RuntimeTool.fetch_task_by_url(ctx, self.target, False)
        event = OnStart(task, fr)
        return RuntimeTool.fire_event(ctx, event)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.target
        del self.fr


class OpFinish(AbsOperator):
    """
    结束当前任务, 并且执行回调
    将所有依赖当前任务的那些任务, 都推入 blocking 栈.
    """

    def __init__(self, url: URL, tid: str):
        self.url = url
        self.tid = tid

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:

        # 变更状态
        task = RuntimeTool.fetch_task(ctx, self.tid)
        # 更新状态.
        task.done(self.url.stage, TaskStatus.FINISHED)

        # 变更状态, 并保存.
        RuntimeTool.store_task(ctx, task)

        runtime = ctx.clone.runtime
        process = runtime.current_process()
        if task.tid == process.root:
            # 根节点结束的话, 任务整体结束. 并回调.
            return self._finish_root(ctx)

        depended_by_map = process.depended_by_map
        if self.tid not in depended_by_map:
            # 没有依赖当前任务的.
            return
        depending = depended_by_map[tid]

        blocking = []
        # 遍历所有依赖当前任务的那些任务.
        for depending_tid in depending:
            ptr = process.get_task(depending_tid)
            if ptr is None:
                continue
            # depending 任务调整为 blocking 任务
            ptr.status = TaskStatus.PREEMPTING
            blocking.append(ptr)

        # 只保存 runtime 变更, 不涉及 data.
        process.store_task(*blocking)
        runtime.store_process(process)
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        # 让调度来解决后续问题.
        return OpSchedule(self.url)

    @classmethod
    def _finish_root(cls, ctx: Context):
        """
        结束根节点, 有必要的话就回调.
        """
        clone = ctx.clone
        runtime = clone.runtime
        process = runtime.current_process()
        process.quit()
        runtime.store_process(process)

        # 如果父进程存在的话, 发起回调.
        if process.parent_id:
            root_task = process.root_task
            tasked = root_task.to_tasked()
            # 异步投递任务.
            ctx.async_input(tasked, process.parent_id, None)
        return None

    def destroy(self) -> None:
        del self.url
        del self.tid


class OpSchedule(AbsOperator):
    """
    调度到一个等待中的任务.
    """

    def __init__(self, fr: URL | None):
        self.fr = fr

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        return

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        blocking = process.preempting
        if len(blocking) > 0:
            return self._preempt(ctx, process, blocking[0])

        waiting = process.waiting
        if len(waiting) > 0:
            return self._preempt(ctx, process, waiting[0])
        return self._preempt(ctx, process, process.root)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _preempt(self, ctx: Context, process: Process, tid: str) -> Optional[Operator]:
        task = process.get_task(tid)
        fr = None
        if self.fr is not None:
            fr = RuntimeTool.fetch_task_by_url(ctx, self.fr, False)
        event = OnPreempt(task, fr)
        return RuntimeTool.fire_event(ctx, event)

    def destroy(self) -> None:
        del self.fr


class OpAwait(AbsOperator):
    """
    让进程进入等待状态
    """

    def __init__(self, current: URL):
        self.current = current

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        runtime = ctx.clone.runtime
        new_wait_task = RuntimeTool.fetch_task_by_url(ctx, self.current, create=True)

        # url 中包含了目标 stage
        new_wait_task.await_at(self.current.stage)

        # 检查 current.
        process = runtime.current_process()
        awaiting_task = process.get_task(process.awaiting)

        # 不是同一个任务才需要保存.
        if new_wait_task.tid != awaiting_task.tid:
            # 应该就是 waiting 状态.
            awaiting_task.status = TaskStatus.WAITING
            # 变更当前 current 状态.
            process.awaiting = new_wait_task.tid
            # 顺序会在最前面.
            process.store_task(awaiting_task)
            runtime.store_process(process)
            RuntimeTool.store_task(ctx, awaiting_task)

        #  注意保存的先后顺序.
        RuntimeTool.store_task(ctx, new_wait_task)
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.current


class OpRepeat(AbsOperator):
    """
    重复当前任务的 current task, 发送消息
    但是不会清空运行中的状态.
    """

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        runtime = ctx.clone.runtime
        # 拿到原始的 process
        process = runtime.current_process()
        awaits_task = runtime.fetch_task(process.awaiting)
        target = awaits_task.url.new_with(stage=awaits_task.await_stage)
        return OpAwait(target)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        pass


class OpRewind(AbsOperator):
    """
    重置当前会话状态, 装作一切没有发生过.
    """

    def __init__(self, repeat: bool = False):
        self.repeat = repeat

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        # rewind 什么也不存
        return

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        ctx.clone.runtime.rewind()
        if self.repeat:
            return OpRepeat()
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.repeat


class OpCancel(AbsOperator):
    """
    取消当前任务, 并层层取消.
    """
    status = TaskStatus.CANCELING

    def __init__(self, current: URL, fr: Optional[URL] = None, reason: Any | None = None,
                 withdraw_list: List[str] = None):
        self.current = current
        self.fr = fr
        self.reason = reason
        if withdraw_list is None:
            withdraw_list = []
        self.withdraw_list: List[str] = withdraw_list

    def _intercept(self, ctx: Context) -> Optional[Operator]:
        # cancel 流程是可以拦截的.
        event_wrapper = self._event()
        current_task = RuntimeTool.fetch_task_by_url(ctx, self.current, False)
        fr_task = None
        if self.fr is not None:
            fr_task = RuntimeTool.fetch_task_by_url(ctx, self.fr, False)

        # 可能是一个 None
        event = event_wrapper(current_task, fr_task, self.reason)
        return RuntimeTool.fire_event(ctx, event)

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        # 走 cancel 流程.
        current_task = RuntimeTool.fetch_task_by_url(ctx, self.current, False)
        if current_task is None:
            # todo
            raise RuntimeException("todo")
        current_task.done(self.current.stage, self.status)

        # 保存变更.
        RuntimeTool.store_task(ctx, current_task)

        # 回调
        canceling = OpCancel.withdraw_depending(ctx, current_task.tid)
        if len(canceling) > 0:
            # 插入到头部.
            canceling.append(*self.withdraw_list)
            self.withdraw_list = canceling
        return None

    def _next(self, ctx: Context) -> Optional[Operator]:
        if len(self.withdraw_list) == 0:
            # 如果根节点也是取消状态. 则进程退出.
            root_task = RuntimeTool.fetch_root_task(ctx)
            if root_task.status != TaskStatus.WAITING:
                RuntimeTool.quit_current_process(ctx)
                # 结束运行.
                return None

            # 如果不是根节点也退出了, 就走正常的调度.
            return OpSchedule(self.current)

        # 继续 cancel
        canceling_id, fr = self.withdraw_list[0]
        self.withdraw_list = self.withdraw_list[1:]

        # 进入下一个 cancel 任务.
        task = RuntimeTool.force_fetch_task(ctx, canceling_id)
        return self.__class__(task.url.copy(), self.current.copy(), self.reason, self.withdraw_list)

    def _event(self) -> Type[Withdrawing]:
        # cancel 流程是可以拦截的.
        return Canceling

    @staticmethod
    def withdraw_depending(ctx: Context, tid: str) -> List[str]:
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        withdraw_task_ids: List[str] = []

        # 依赖当前任务的各种任务都会进入 withdraw 队列.
        depended_by_map = process.depended_by_map
        depending = depended_by_map.get(tid, None)
        # 为空
        if depending is None:
            return withdraw_task_ids

        for tid in depending:
            ptr = process.get_task(tid)
            if ptr is not None:
                withdraw_task_ids.append(ptr.tid)
        return withdraw_task_ids

    def destroy(self) -> None:
        del self.current
        del self.fr
        del self.withdraw_list
        del self.reason


class OpFail(OpCancel):
    """
    当前任务失败, 会向上返回失败.
    走的是和 Cancel 一样的流程, 只是事件不同.
    """
    status = TaskStatus.FAILING

    def _event(self) -> Type[Withdrawing]:
        return Failing


class OpQuit(OpCancel):
    """
    退出所有的任务.
    每一个任务可以拦截
    """
    status = TaskStatus.CANCELING

    def _event(self) -> Type[Withdrawing]:
        return Quiting

    def _next(self, ctx: Context) -> Optional[Operator]:
        if len(self.withdraw_list) > 0:
            # 继续走依赖关系的取消流程.
            return super()._next(ctx)

        process = ctx.clone.runtime.current_process()
        # blocking 优先.
        blocking = process.preempting
        if len(blocking) > 0:
            self.withdraw_list = [blocking[0]]
            return super()._next(ctx)
        waiting = process.waiting
        if len(waiting) > 0:
            self.withdraw_list = [waiting[0]]
            return super()._next(ctx)
        yielding = process.yielding
        if len(yielding) > 0:
            self.withdraw_list = [yielding[0]]
        # process 结束.
        process.quit()
        return None


class OpDependOn(AbsOperator):

    def __init__(self, this: Thought, target: URL, force: bool = False):
        self.this: Thought = this
        self.target_url: URL = target
        self._target: Optional[Thought] = None
        self.force = force

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        """
        depend 事件可以被终止.
        """
        # target = RuntimeTool.fetch_thought(ctx, self.target_url)
        target_task = RuntimeTool.fetch_task(ctx, self.target_url, or_create=True)
        match target_task.status:
            case TaskStatus.FINISHED:
                #  目标任务已经完成的话, 直接回调.
                target = RuntimeTool.fetch_thought_by_task(ctx, target_task)
                return OpCallback(self.this, target)
            case _:
                # 否则出发一次 OnDepended 事件, 允许被拦截中断.
                target = RuntimeTool.fetch_thought_by_task(ctx, target_task)
                this_url = RuntimeTool.thought_to_url(self.this)
                event = OnDepended(target, this_url)
                return RuntimeTool.fire_event_with_thought(ctx, event)

    def _get_target(self, ctx: "Context") -> Thought:
        if self._target is None:
            self._target = RuntimeTool.new_thought(ctx, self.target_url)
        return self._target

    def _save_change(self, ctx: "Context") -> None:
        target = self._get_target(ctx)

        task = RuntimeTool._fetch_task_by_thought(ctx, self.this)
        task.status = TaskStatus.DEPENDING
        task.callbacks = target.tid
        # 保存当前的 task
        ctx.clone.runtime.store_task(task)
        return

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        target = self._get_target(ctx)
        if self.force:
            # 强制重启.
            return OpRestart(target)
        # 进入目标任务.
        this_url = RuntimeTool.thought_to_url(self.this)
        return OpRedirect(target, this_url, intercept=True)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.this
        del self.target_url
        del self._target
        del self.force


class OpRedirect(AbsOperator):

    def __init__(self, this: Thought, to: URL, intercept: bool = True):
        self.this = this
        self.to = to
        self.intercept = intercept
        self.this_url = RuntimeTool.thought_to_url(this)
        self.__target: Optional[Thought] = None

    def target_thought(self, ctx: Context) -> Thought:
        if self.__target is None:
            self.__target = RuntimeTool.new_thought(ctx, self.to)
        return self.__target

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        if not self.intercept:
            return None

        target = self.target_thought(ctx)

        if self.this.tid != target.tid:
            event = OnActivate(target, self.this_url)
            return RuntimeTool.fire_event_with_thought(ctx, event)

        if self.this.stage == self.to.stage:
            raise RuntimeException("todo: order")
        return OpGoStage(self.this, self.to.stage)

    def _save_change(self, ctx: "Context") -> None:
        return

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        target = self.target_thought(ctx)
        task = RuntimeTool._fetch_task_by_thought(ctx, target)
        match task.status:
            case TaskStatus.PREEMPTING, TaskStatus.DEPENDING, TaskStatus.YIELDING, TaskStatus.RUNNING:
                event = OnPreempt(target, self.this_url)
                return RuntimeTool.fire_event_with_thought(ctx, event)
            case _:
                return OpRestart(target)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        pass

    def destroy(self) -> None:
        del self.this
        del self.this_url
        del self.to
        del self.__target


class OpRestart(AbsOperator):

    def __init__(self, this: Thought):
        self.this = this

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        task = RuntimeTool._fetch_task_by_thought(ctx, self.this)
        task.restart()
        RuntimeTool.save_task(ctx, task)
        return

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        event = OnStart(self.this)
        return RuntimeTool.fire_event_with_thought(ctx, event)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.this


class OpCallback(AbsOperator):

    def __init__(self, this: Thought, fr: Thought):
        self.this = this
        self.fr = fr

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        task = RuntimeTool._fetch_task_by_thought(ctx, self.this)
        task.status = TaskStatus.RUNNING
        RuntimeTool.save_task(ctx, task)
        self.this = RuntimeTool.merge_thought_from_task(self.this, task)
        return

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        event = Callback(self.this, self.fr.matched())
        return RuntimeTool.fire_event_with_thought(ctx, event)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        pass

    def destroy(self) -> None:
        del self.this
        del self.fr


class OpReset(AbsOperator):
    """
    重置进程
    """

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        process.reset()
        runtime.store_process(process)
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        process = ctx.clone.runtime.current_process()
        task = process.root_task
        thought = RuntimeTool.fetch_thought_by_task(ctx, task)
        event = OnStart(thought)
        return RuntimeTool.fire_event_with_thought(ctx, event)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        pass


class OpYieldTo(AbsOperator):

    def __init__(self, this: Thought, to: URL, pid: str | None):
        self.this = this
        self.to = to
        self.pid = pid

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        """
        depend 事件可以被终止.
        """
        target_task = RuntimeTool.fetch_task(ctx, self.to, or_create=False)
        if not target_task:
            return None

        # 目标任务已经完成的情况.
        if target_task.status == TaskStatus.FINISHED:
            #  目标任务已经完成的话, 直接回调.
            target = RuntimeTool.fetch_thought_by_task(ctx, target_task)
            return OpCallback(self.this, target)
        return None

    def _save_change(self, ctx: "Context") -> None:
        task = RuntimeTool._fetch_task_by_thought(ctx, self.this)
        task.status = TaskStatus.YIELDING
        target_id = RuntimeTool.new_tid(ctx, self.to)
        task.callbacks = target_id
        runtime = ctx.clone.runtime
        runtime.store_task(task)
        process = runtime.current_process()

        # 创建并保存异步进程.
        target_task = RuntimeTool.fetch_task(ctx, self.to, or_create=True)
        sub_process = process.new_process(process.sid, target_task, self.pid, process.pid)
        runtime.store_process(sub_process)

        # 发送异步消息.
        ctx.send(self.this).async_input(
            Payload.Action("start"),
            sub_process.pid
        )
        return

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        url = RuntimeTool.thought_to_url(self.this)
        return OpSchedule(url)

    def destroy(self) -> None:
        del self.this
        del self.to


class IOperatorManager(OperationManager):
    def __init__(self, ctx: Context, this: Thought):
        self.ctx = ctx
        self.this = this

    def destroy(self) -> None:
        del self.ctx
        del self.this

    def go_stage(self, *stages: str) -> Operator:
        try:
            op = OpGoStage(self.this, *stages)
            return op
        finally:
            self.destroy()

    def redirect_to(self, to: "URL") -> "Operator":
        """
        从当前对话任务, 进入一个目标对话任务.
        """
        try:
            op = OpRedirect(self.this, to, intercept=False)
            return op
        finally:
            self.destroy()

    def repeat(self) -> Operator:
        try:
            return OpRepeat(self.this)
        finally:
            self.destroy()

    def rewind(self, repeat: bool = False) -> Operator:
        try:
            return OpRewind(self.this, repeat)
        finally:
            self.destroy()

    def wait(self) -> Operator:
        try:
            return OpAwait(self.this)
        finally:
            self.destroy()

    def forward(self) -> Operator:
        try:
            return OpForwardStage(self.this)
        finally:
            self.destroy()

    def finish(self) -> Operator:
        try:
            return OpFinish(self.this)
        finally:
            self.destroy()

    def cancel(self, reason: Optional[Any]) -> Operator:
        try:
            return OpCancel(self.this, reason=reason)
        finally:
            self.destroy()

    @abstractmethod
    def intend_to(self, url: URL, params: Dict | None = None) -> "Operator":
        try:
            this_url = RuntimeTool.thought_to_url(self.this)
            return OpIntendTo(url, params, this_url, route=False)
        finally:
            self.destroy()

    def reset(self) -> Operator:
        try:
            return OpReset()
        finally:
            self.destroy()

    def restart(self) -> "Operator":
        try:
            return OpRestart(self.this)
        finally:
            self.destroy()

    def quit(self, reason: Optional[Any]) -> Operator:
        try:
            return OpQuit(self.this, reason=reason)
        finally:
            self.destroy()

    def fail(self, reason: Optional[Any]) -> Operator:
        try:
            return OpFail(self.this, reason=reason)
        finally:
            self.destroy()

    def depend_on(self, on: URL, force: bool = False) -> Operator:
        try:
            return OpDependOn(self.this, on, force=force)
        finally:
            self.destroy()

    def yield_to(self, to: URL, pid: Optional[str] = None) -> Operator:
        try:
            return OpYieldTo(self.this, to, pid)
        finally:
            self.destroy()
