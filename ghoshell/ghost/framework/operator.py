from abc import ABCMeta, abstractmethod
from typing import Optional, Dict, List, Any, Tuple

from ghoshell.ghost import Context, CtxTool, UML, Process, IntentionMeta, Event
from ghoshell.ghost import MissUnderstoodException, RuntimeException
from ghoshell.ghost import OnCallback
from ghoshell.ghost import OnCancel, OnFailed, OnQuit
from ghoshell.ghost import OnDepended, OnRedirect
from ghoshell.ghost import OnFallback, OnIntend, OnRepeat
from ghoshell.ghost import OnPreempt, OnStart
from ghoshell.ghost import Operator, OperationManager
from ghoshell.ghost import Task, TaskStatus, TaskLevel
from ghoshell.ghost import Thought


class AbsOperator(Operator, metaclass=ABCMeta):

    def run(self, ctx: "Context") -> Optional["Operator"]:
        interceptor = self._intercept(ctx)
        if interceptor is not None:
            return interceptor
        self._save_change(ctx)
        event_op = self._fire_event(ctx)
        if event_op is not None:
            return event_op
        return self._next(ctx)

    @abstractmethod
    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        pass

    @abstractmethod
    def _save_change(self, ctx: "Context") -> None:
        pass

    @abstractmethod
    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        pass

    @abstractmethod
    def _next(self, ctx: "Context") -> Optional["Operator"]:
        pass


class OpReceiveInput(Operator):
    """
    todo: ??
    接受到一个 Input, 启动默认的处理流程.
    会根据 root -> current 任务生成一个意图树
    """

    def run(self, ctx: "Context") -> Optional[Operator]:
        runtime = ctx.clone.runtime
        _input = ctx.input
        process = runtime.current_process()
        # tid 不为空的情况:
        if _input.message.tid:
            exists = runtime.fetch_task(_input.message.tid)
            if exists is not None:
                return OpIntentTo(exists)

        # 判断是不是一个异步回调消息.
        callback_task_id = self.is_async_callback(ctx)
        if callback_task_id is not None:
            # 处理异步回调任务消息
            return OpAsyncCallback(callback_task_id)

        # 检查是否匹配到某个 attentions
        matched = self.match_attentions(ctx, process)
        if matched is not None:
            return OpAttendTo(matched.uml, matched.args)

        # 检查是否匹配了全局的 intentions
        matched = self.match_intention(ctx, process)
        if matched is not None:
            return OpIntentTo(matched.uml, matched.args)

        # 没有匹配到任何意图, 则走 fallback 流程.
        return OpFallback()

    class Matched:
        def __init__(self, matched: UML, args: Optional[Dict]):
            self.uml = matched
            self.args = args

    def is_async_callback(self, ctx: "Context") -> Optional[str]:
        # todo
        # 判断是否是异步回调消息
        return None

    @classmethod
    def match_attentions(cls, ctx: "Context", process: Process) -> Optional[Matched]:
        """
        将进程的 attentions 生成出来
        用来从 ctx 中匹配一个目标意图.
        """
        # 添加 current
        current_task = process.tasks.get(process.awaiting)
        attention_metas = cls.attention_metas(ctx, process, current_task)
        attentions = ctx.attentions
        predefined_kinds = attentions.intention_kinds()
        for kind in predefined_kinds:
            if kind not in attention_metas:
                continue
            metas = attention_metas[kind]
            for meta in metas:
                matched, args = attentions.match(ctx, meta)
                matched: Optional[UML] = None
                if matched:
                    return OpReceiveInput.Matched(matched, args)
        return None

    @classmethod
    def match_intention(cls, ctx: "Context", process: Process) -> Optional[Matched]:
        # 如果当前任务是 public 级别的任务, 则允许做意图的模糊匹配.
        # 意图的模糊匹配并不精确到参数上. 需要二次加工.
        current_task = process.tasks.get(process.awaiting)
        if current_task.level != TaskLevel.LEVEL_PUBLIC:
            return None
        attentions = ctx.attentions
        matched = attentions.wildcard_match(ctx)
        if matched is not None:
            return OpReceiveInput.Matched(matched, None)
        return None

    @classmethod
    def attention_metas(cls, ctx: "Context", process: Process, current_task: Task) -> Dict[str, List[IntentionMeta]]:
        """
        从进程中获取当前匹配的意图.
        """
        result: Dict[str, List[IntentionMeta]] = {}
        # 第一步, 添加 root
        root_ptr = process.tasks.get(process.root)
        cls._add_intention_meta_to_attentions(ctx, result, root_ptr)

        if process.awaiting != root_ptr:
            cls._add_intention_meta_to_attentions(ctx, result, current_task)

        # 封闭域任务, 不再继续增加注意目标.
        if current_task.level <= TaskLevel.LEVEL_PRIVATE:
            return result

        # 第三步, 添加 waiting 中的节点的意图.
        for tid in process.waiting:
            blocking = process.tasks.get(tid)
            cls._add_intention_meta_to_attentions(ctx, result, blocking)
        return result

    @classmethod
    def _add_intention_meta_to_attentions(
            cls,
            ctx: Context,
            result: Dict[str, List[IntentionMeta]],
            task_ptr: Task,
    ) -> Dict[str, List[IntentionMeta]]:
        # 初始化
        # 上下文中生成意图树.
        for uml in task_ptr.attentions:
            stage = CtxTool.fetch_stage(ctx, uml)
            # 从 stage 里生成 intention
            intention = stage.intention(ctx)
            if not intention:
                continue
            # 从 intention 里拿到 metas
            metas = intention.metas()
            for meta in metas:
                kind = meta.kind
                if kind not in result:
                    result[kind] = []
                result[kind].append(meta)
        return result

    def destroy(self) -> None:
        pass


class OpAsyncCallback(Operator):
    """
    todo: 接受到了一个异步的回调.
    """

    def __init__(self, callback_task_id: str):
        self.callback_task_id = callback_task_id
        super().__init__()

    def run(self, ctx: "Context") -> Optional[Operator]:
        return None

    def destroy(self) -> None:
        del self.callback_task_id


class OpFallback(AbsOperator):
    """
    没有任何意图被匹配到时.
    """

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
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
        raise MissUnderstoodException("todo")

    @classmethod
    def fallback_to_task(cls, ctx: "Context", task: Task) -> Optional[Operator]:
        # 当前任务.  fallback
        thought = CtxTool.fetch_thought_by_task(ctx, task)
        event = OnFallback(thought, None)
        return CtxTool.fire_event(ctx, event)

    def destroy(self) -> None:
        pass


class OpAttendTo(Operator):
    """
    todo: ???
    """

    def __init__(self, to: UML, args: Optional[Dict]):
        self.to = to
        self.args = args
        super().__init__()

    def run(self, ctx: "Context") -> Optional[Operator]:
        pass

    def destroy(self) -> None:
        del self.to
        del self.args


class OpIntentTo(Operator):
    """
    todo: ???
    命中了一个意图, 前往目标任务.
    过程中生产一个事件, 如果没问题的话就正式激活目标任务.
    """

    def __init__(self, to: Task, args: Optional[Dict] = None):
        # 匹配的目标
        self.to: Task = to
        # 匹配的参数, 如果为 none 的话还需要二次检查.
        self.args: Optional[Dict] = args
        super().__init__()

    def run(self, ctx: "Context") -> Optional[Operator]:
        process = ctx.clone.runtime.current_process()
        current_task = process.current_task()
        to_thought = ctx.thought(self.to)

        if self.args is None:
            # 用 intention 重新匹配一次.
            stage = CtxTool.fetch_stage(ctx, to_thought.uml)
            self.args = stage.intention(ctx).match(ctx)

        # 意图命中了自身.
        event = OnIntend(to_thought, self.args, current_task.uml)
        return fire_event(ctx, event)

        # 如果不是新建的任务
        if to_thought.status != TaskStatus.NEW:
            event = OnIntend(to_thought)
            # 是否任务被拦截.
            interceptor = CtxTool.fire_event(ctx, event)
            if interceptor is not None:
                return interceptor

    @staticmethod
    def on_intercept(ctx: "Context", process: Process) -> Optional[Operator]:
        current_task_ptr = process.tasks.get(process.awaiting)
        current_thought = ctx.thought(current_task_ptr.uml)
        event = Event(current_thought, Event.ON_INTERCEPT)

    def on_intend_to(self):
        pass

    def destroy(self) -> None:
        pass


class OpGoStage(AbsOperator):
    """
    当前任务切换一个 stage.
    """

    def __init__(self, thought: Thought, *stages: str):
        self.this = thought
        self.forwards: Tuple = stages

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        task = CtxTool.fetch_task_by_thought(ctx, self.this)
        # 将 stages 插入到前面.
        if len(self.forwards) > 0:
            task.add_stages(*self.forwards)
        # 离开时保存.
        task = CtxTool.complete_task(ctx, task)
        ctx.clone.runtime.store_task(task)
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return OpForwardStage(self.this)

    def destroy(self) -> None:
        del self.this
        del self.forwards


class OpForwardStage(AbsOperator):
    """
    推进状态机往前走一格, 如果 task 栈中有节点, 则运行.
    没有节点的话, 进入 finish 操作.
    """

    def __init__(self, this: Thought):
        self.this: Thought = this
        self.fr: UML = CtxTool.thought_to_uml(this)

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        this = self.this
        process = ctx.clone.runtime.current_process()
        ptr = process.get_task(this.tid)
        if ptr is not None and len(ptr.forwards) == 0:
            return OpFinish(self.this)
        return None

    def _save_change(self, ctx: "Context") -> None:
        task = CtxTool.fetch_task_by_thought(ctx, self.this)
        task.forward()
        ctx.clone.runtime.store_task(task)
        self.this = CtxTool.merge_thought_from_task(self.this, task)
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        # 触发事件, 等待事件提供的后续流程.
        return OpStart(self.this, self.fr)

    def destroy(self) -> None:
        del self.this
        del self.fr


class OpStart(AbsOperator):

    def __init__(self, this: Thought, fr: Optional[UML] = None):
        self.this = this
        self.fr = fr

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        return None

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        event = OnStart(self.this, self.fr)
        return CtxTool.fire_event(ctx, event)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.this


class OpFinish(AbsOperator):
    """
    结束当前任务, 并且执行回调
    将所有依赖当前任务的那些任务, 都推入 blocking 栈.
    """

    def __init__(self, this: Thought):
        self.this = this

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        # 变更状态
        this = self.this
        tid = this.tid
        task = CtxTool.fetch_task_by_thought(ctx, this)
        # 更新状态.
        task.done(TaskStatus.FINISHED)

        # 变更状态, 并保存.
        runtime = ctx.clone.runtime
        runtime.store_task(task)

        process = runtime.current_process()
        depended_by_map = process.depended_by_map
        if tid not in depended_by_map:
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
            ptr.status = TaskStatus.BLOCKING
            blocking.append(ptr)

        # 只保存 runtime 变更, 不涉及 data.
        process.store_task(*blocking)
        runtime.store_process(process)
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        # 让调度来解决后续问题.
        # 回调到 blocking, 然后是 waiting.
        this_uml = CtxTool.thought_to_uml(self.this)
        return OpSchedule(this_uml)

    def destroy(self) -> None:
        del self.this


class OpSchedule(AbsOperator):
    """
    调度到一个等待中的任务.
    """

    def __init__(self, fr: UML):
        self.fr = fr

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        blocking = process.blocking
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
        thought = CtxTool.fetch_thought_by_task(ctx, task)
        event = OnPreempt(thought, self.fr)
        return CtxTool.fire_event(ctx, event)

    def destroy(self) -> None:
        del self.fr


class OpAwait(AbsOperator):
    """
    让进程进入等待状态
    """

    def __init__(self, this: Thought):
        self.this: Thought = this

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        # 先保存当前状态.
        runtime = ctx.clone.runtime
        new_wait_task = CtxTool.fetch_task_by_thought(ctx, self.this, or_create=True)
        new_wait_task.status = TaskStatus.RUNNING
        runtime.store_task(new_wait_task)

        # 检查 current.
        process = runtime.current_process()
        await_task_ptr = process.get_task(process.awaiting)

        # 不是同一个任务才需要保存.
        if new_wait_task.tid != await_task_ptr.tid:
            await_task_ptr.status = TaskStatus.RUNNING
            # 变更当前 current 状态.
            process.awaiting = new_wait_task.tid
            # 顺序会在最前面.
            process.store_task(await_task_ptr)
        runtime.store_process(process)
        return None

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.this


class OpRepeat(AbsOperator):
    """
    重复当前任务的 current task, 发送消息
    但是不会清空运行中的状态.
    """

    def __init__(self, this: Thought):
        this.status = TaskStatus.RUNNING
        self.this = this

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        CtxTool.save_thought(ctx, self.this)
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        runtime = ctx.clone.runtime
        # 拿到原始的 process
        process = runtime.current_process()
        awaits_task = runtime.fetch_task(process.awaiting)
        if awaits_task.tid == self.this.tid:
            thought = self.this
        else:
            thought = CtxTool.fetch_thought_by_task(ctx, awaits_task)
        # 重新启动 awaits 任务.
        this_uml = CtxTool.thought_to_uml(self.this)
        event = OnRepeat(thought, this_uml)
        return CtxTool.fire_event(ctx, event)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.this


class OpRewind(AbsOperator):
    """
    重置当前会话状态, 装作一切没有发生过.
    """

    def __init__(self, this: Thought, repeat: bool = False):
        self.this = this
        self.repeat = repeat

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        # rewind 什么也不存
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        ctx.clone.runtime.rewind()
        if self.repeat:
            return OpRepeat(self.this)
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.this
        del self.repeat


class OpCancel(AbsOperator):
    """
    取消当前任务, 并层层取消.
    """
    status = TaskStatus.CANCELED

    def __init__(self, this: Thought, reason: Any, fr: Optional[UML] = None):
        self.this = this
        self.reason = reason
        self.fr = fr
        self.withdraw_list: List[Tuple[str, UML]] = []

    def _intercept(self, ctx: Context) -> Optional[Operator]:
        # cancel 流程是可以拦截的.
        event = self._event()
        return CtxTool.fire_event(ctx, event)

    def _save_change(self, ctx: Context) -> None:
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        # 走 cancel 流程.
        current_ptr = process.get_task(self.this.tid)
        current_ptr.done(self.status)

        # 保存变更.
        process.store_task(current_ptr)
        runtime.store_process(process)

        canceling = OpCancel.withdraw_depending(ctx, self.this.tid)
        uml = CtxTool.thought_to_uml(self.this)
        if len(canceling) > 0:
            for tid in canceling:
                self.withdraw_list.append((tid, uml))

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _next(self, ctx: Context) -> Optional[Operator]:
        if len(self.withdraw_list) == 0:
            return None

            # 继续 cancel
        canceling_id, fr = self.withdraw_list[0]
        self.withdraw_list = self.withdraw_list[1:]

        # 进入下一个 cancel 任务.
        task = ctx.clone.runtime.fetch_task(canceling_id)
        _next = CtxTool.fetch_thought_by_task(ctx, task)
        self.this = _next
        self.fr = fr
        return self

    def _event(self) -> Optional[Event]:
        # cancel 流程是可以拦截的.
        return OnCancel(self.this, fr=self.fr, reason=self.reason)

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
        del self.this
        del self.fr
        del self.withdraw_list
        del self.reason


class OpFail(OpCancel):
    """
    当前任务失败, 会向上返回失败.
    走的是和 Cancel 一样的流程, 只是事件不同.
    """
    status = TaskStatus.FAILED

    def _event(self) -> Optional[Event]:
        return OnFailed(self.this, fr=self.fr, reason=self.reason)


class OpQuit(OpCancel):
    """
    退出所有的任务.
    每一个任务可以拦截
    """
    status = TaskStatus.CANCELED

    def _event(self) -> Optional[Event]:
        return OnQuit(self.this, fr=self.fr, reason=self.reason)

    def _next(self, ctx: Context) -> Optional[Operator]:
        if len(self.withdraw_list) > 0:
            # 继续走依赖关系的取消流程.
            return super()._next(ctx)
        process = ctx.clone.runtime.current_process()
        # blocking 优先.
        blocking = process.blocking
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

    def __init__(self, this: Thought, target: UML, force: bool = False):
        self.this: Thought = this
        self.target_uml: UML = target
        self._target: Optional[Thought] = None
        self.force = force

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        """
        depend 事件可以被终止.
        """
        # target = CtxTool.fetch_thought(ctx, self.target_uml)
        target_task = CtxTool.fetch_task(ctx, self.target_uml, or_create=True)
        match target_task.status:
            case TaskStatus.FINISHED:
                #  目标任务已经完成的话, 直接回调.
                target = CtxTool.fetch_thought_by_task(ctx, target_task)
                return OpCallback(self.this, target)
            case _:
                # 否则出发一次 OnDepended 事件, 允许被拦截中断.
                target = CtxTool.fetch_thought_by_task(ctx, target_task)
                this_uml = CtxTool.thought_to_uml(self.this)
                event = OnDepended(target, this_uml)
                return CtxTool.fire_event(ctx, event)

    def _get_target(self, ctx: "Context") -> Thought:
        if self._target is None:
            self._target = CtxTool.fetch_thought(ctx, self.target_uml)
        return self._target

    def _save_change(self, ctx: "Context") -> None:
        target = self._get_target(ctx)

        task = CtxTool.fetch_task_by_thought(ctx, self.this)
        task.status = TaskStatus.DEPENDING
        task.depending = target.tid
        # 保存当前的 task
        ctx.clone.runtime.store_task(task)
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        target = self._get_target(ctx)
        if self.force:
            # 强制重启.
            return OpRestart(target)
        # 进入目标任务.
        this_uml = CtxTool.thought_to_uml(self.this)
        return OpRedirect(target, this_uml, intercept=True)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.this
        del self.target_uml
        del self._target
        del self.force


class OpRedirect(AbsOperator):

    def __init__(self, this: Thought, to: UML, intercept: bool = True):
        self.this = this
        self.to = to
        self.intercept = intercept
        self.this_uml = CtxTool.thought_to_uml(this)
        self.__target: Optional[Thought] = None

    def target_thought(self, ctx: Context) -> Thought:
        if self.__target is None:
            self.__target = CtxTool.fetch_thought(ctx, self.to)
        return self.__target

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        if not self.intercept:
            return None

        target = self.target_thought(ctx)

        if self.this.tid != target.tid:
            event = OnRedirect(target, self.this_uml)
            return CtxTool.fire_event(ctx, event)

        if self.this.stage == self.to.stage:
            raise RuntimeException("todo: order")
        return OpGoStage(self.this, self.to.stage)

    def _save_change(self, ctx: "Context") -> None:
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        target = self.target_thought(ctx)
        task = CtxTool.fetch_task_by_thought(ctx, target)
        match task.status:
            case TaskStatus.BLOCKING, TaskStatus.DEPENDING, TaskStatus.YIELDING, TaskStatus.RUNNING:
                event = OnPreempt(target, self.this_uml)
                return CtxTool.fire_event(ctx, event)
            case _:
                return OpRestart(target)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        pass

    def destroy(self) -> None:
        del self.this
        del self.this_uml
        del self.to
        del self.__target


class OpRestart(AbsOperator):

    def __init__(self, this: Thought):
        self.this = this

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        task = CtxTool.fetch_task_by_thought(ctx, self.this)
        task.reset()
        CtxTool.save_task(ctx, task)
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        event = OnStart(self.this)
        return CtxTool.fire_event(ctx, event)

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
        task = CtxTool.fetch_task_by_thought(ctx, self.this)
        task.status = TaskStatus.RUNNING
        CtxTool.save_task(ctx, task)
        self.this = CtxTool.merge_thought_from_task(self.this, task)
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        event = OnCallback(self.this, self.fr.result())
        return CtxTool.fire_event(ctx, event)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        pass

    def destroy(self) -> None:
        del self.this
        del self.fr


class OpReset(Operator):
    """
    重置进程
    """

    def run(self, ctx: "Context") -> Optional[Operator]:
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        process.reset()
        runtime.store_process(process)
        return None

    def destroy(self) -> None:
        pass


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

    def redirect_to(self, to: "UML") -> "Operator":
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

    def depend_on(self, on: UML, force: bool = False) -> Operator:
        try:
            return OpDependOn(self.this, on, force=force)
        finally:
            self.destroy()

    def yield_to(self, to: UML, pid: Optional[str] = None) -> Operator:
        pass
