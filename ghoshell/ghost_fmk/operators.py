from abc import ABCMeta, abstractmethod
from typing import Optional, Dict, List, Any, Tuple

from ghoshell.ghost import Context, CtxTool, UML, Process, Intention, Event
from ghoshell.ghost import MissUnderstoodException, RuntimeException
from ghoshell.ghost import OnCallback
from ghoshell.ghost import OnCancel, OnFailed, OnQuit
from ghoshell.ghost import OnDepended, OnRedirect
from ghoshell.ghost import OnFallback, OnIntend, OnRepeat, OnAttend
from ghoshell.ghost import OnPreempt, OnStart
from ghoshell.ghost import Operator, OperationManager
from ghoshell.ghost import Payload, StateMsg
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

    def enqueue(self, ctx: "Context") -> Optional[List["Operator"]]:
        return None

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


class OpReceive(AbsOperator):

    def __init__(self):
        self.enqueued = False

    class Matched:
        def __init__(self, matched: UML, args: Optional[Dict]):
            self.uml = matched
            self.args = args

    def enqueue(self, ctx: "Context") -> Optional[List["Operator"]]:
        if self.enqueued:
            return None
        self.enqueued = True

        enqueue: List[Operator] = []
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        if process.is_new:
            root = process.root_task
            root_thought = CtxTool.fetch_thought_by_task(ctx, root)
            enqueue.append(OpStart(root_thought))
            process.round += 1
            runtime.store_process(process)

        # 检查 payload 的 tid
        _input = ctx.input
        payload = _input.payload
        op = self._payload_tid_op(ctx, payload)
        if op is not None:
            enqueue.append(op)

        # 继续检查 payload action
        op = self._payload_state_op(ctx, payload)
        if op is not None:
            enqueue.append(op)
        return enqueue

    @classmethod
    def _payload_tid_op(cls, ctx: Context, payload: Payload) -> Optional[Operator]:
        if not payload.tid:
            return None
        payload_task = CtxTool.fetch_task_by_tid(ctx, payload.tid)
        if payload_task is None:
            return None
        if payload_task.status != TaskStatus.RUNNING:
            return None
        payload_thought = CtxTool.fetch_thought_by_task(ctx, payload_task)
        return OpAwait(payload_thought)

    @classmethod
    def _payload_state_op(cls, ctx: Context, payload: Payload) -> Optional[Operator]:
        if payload.state is None:
            return None
        state = payload.state
        state_task = CtxTool.fetch_task(ctx, state.uml, or_create=True)
        if state.vars is not None:
            state_task.vars = state.vars
        ctx.clone.runtime.store_task(state_task)
        # 匹配动作.
        action = state.action
        if action == "":
            return None

        thought = CtxTool.fetch_thought_by_task(ctx, state_task)
        match state.action:
            case StateMsg.ON_START:
                return OpStart(thought)
            case StateMsg.ON_QUIT:
                return OpQuit(thought, "state action")
            case StateMsg.ON_RESET:
                return OpReset()
            case StateMsg.ON_CANCEL:
                return OpCancel(thought, "state action")
            case StateMsg.ON_FINISH:
                return OpFinish(thought)
            case _:
                return None

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        # 检查是否匹配到某个 attentions
        matched = self.match_attentions(ctx)
        if matched is not None:
            return OpIntendTo(matched.uml, matched.result, attend=True)

        # 检查是否匹配了全局的 attentions
        matched = self.match_intentions(ctx)
        if matched is not None:
            return OpIntendTo(matched.uml, matched.result, attend=False)
        return None

    def _save_change(self, ctx: "Context") -> None:
        pass

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        pass

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return OpFallback()

    @classmethod
    def match_attentions(cls, ctx: "Context") -> Optional[Intention]:
        """
        将进程的 attentions 生成出来
        用来从 ctx 中匹配一个目标意图.
        """
        # 添加 current
        attention_metas = cls.attention_metas(ctx)
        attentions = ctx.clone.attentions
        predefined_kinds = attentions.kinds()
        # 只能匹配已有的.
        for kind in predefined_kinds:
            if kind not in attention_metas:
                continue
            # 匹配所有的 metas
            metas = attention_metas[kind]
            matched = attentions.match(ctx, *metas)
            if matched is not None:
                return matched
        return None

    @classmethod
    def match_intentions(cls, ctx: "Context") -> Optional[Intention]:
        # 如果当前任务是 public 级别的任务, 则允许做意图的模糊匹配.
        # 意图的模糊匹配并不精确到参数上. 需要二次加工.
        process = ctx.clone.runtime.current_process()
        attentions = ctx.clone.attentions
        awaiting_task = process.awaiting_task

        intention_metas = cls.intention_metas(ctx)
        predefined_kinds = attentions.kinds()
        for kind in predefined_kinds:
            if kind not in intention_metas:
                continue
            # 匹配所有的 metas
            metas = intention_metas[kind]
            matched = attentions.match(ctx, *metas)
            if matched is not None:
                return matched

        if awaiting_task.level < TaskLevel.LEVEL_PUBLIC:
            return None

        # 模糊匹配.
        return attentions.wildcard_match(ctx)

    @classmethod
    def intention_metas(cls, ctx: "Context") -> Dict[str, List[Intention]]:
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        awaiting_task = process.awaiting_task
        result: Dict[str, List[Intention]] = {}

        # protected 才允许回溯匹配.
        if awaiting_task.level < TaskLevel.LEVEL_PROTECTED:
            return result

        blocking = process.blocking
        for tid in blocking:
            blocking_task = process.get_task(tid)
            result = cls._add_task_intention_to_attentions(ctx, result, blocking_task, attentions=False)

        # 检查 waiting.
        waiting = process.waiting
        for tid in waiting:
            waiting_task = process.get_task(tid)
            result = cls._add_task_intention_to_attentions(ctx, result, waiting_task, attentions=False)

        # 添加 awaiting
        if process.awaiting != process.root:
            root_task = process.root_task
            result = cls._add_task_intention_to_attentions(ctx, result, root_task, attentions=False)

        return result

    @classmethod
    def attention_metas(cls, ctx: "Context") -> Dict[str, List[Intention]]:
        """
        从进程中获取当前匹配的意图.
        """
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        result: Dict[str, List[Intention]] = {}

        # 第一步, 添加 root
        root_task = process.root_task
        result = cls._add_task_intention_to_attentions(ctx, result, root_task)

        awaiting_task = process.awaiting_task
        # 添加 awaiting
        if process.awaiting != process.root:
            result = cls._add_task_intention_to_attentions(ctx, result, awaiting_task)

        # 封闭域任务, 不再继续增加注意目标.
        if awaiting_task.level < TaskLevel.LEVEL_PROTECTED:
            return result

        # 第三步, 添加 waiting 中的节点的意图.
        for tid in process.waiting:
            waiting = process.get_task(tid)
            result = cls._add_task_intention_to_attentions(ctx, result, waiting)
        return result

    @classmethod
    def _add_task_intention_to_attentions(
            cls,
            ctx: Context,
            result: Dict[str, List[Intention]],
            task: Task,
            attentions: bool = True,
    ) -> Dict[str, List[Intention]]:
        # 初始化
        # 上下文中生成意图树.
        if attentions:
            uml_list = task.attentions
        else:
            uml_list = CtxTool.task_to_uml(task)

        for uml in uml_list:
            stage = CtxTool.fetch_stage(ctx, uml.think, uml.stage)
            if stage is None:
                continue
            # 从 stage 里生成 intention
            intentions = stage.intentions(ctx)
            if not intentions:
                continue
            # 从 intention 里拿到 metas
            for meta in intentions:
                kind = meta.KIND
                if kind not in result:
                    result[kind] = []
                result[kind].append(meta)
        return result

    def destroy(self) -> None:
        del self.enqueued


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


class OpIntendTo(AbsOperator):
    """
    todo: ???
    命中了一个意图, 前往目标任务.
    过程中生产一个事件, 如果没问题的话就正式激活目标任务.
    """

    def __init__(self, to: UML, params: Optional[Dict] = None, fr: UML | None = None, attend: bool = False):
        # 匹配的目标
        self.to: UML = to
        # 匹配的参数, 如果为 none 的话还需要二次检查.
        self.fr = fr
        self.params: Optional[Dict] = params
        self.attend = attend

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _save_change(self, ctx: "Context") -> None:
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        this = CtxTool.fetch_thought(ctx, self.to)
        params = self.params
        if params is None:
            stage = CtxTool.fetch_stage(ctx, self.to.think, self.to.think)
            intentions = stage.intentions()
            if intentions is not None:
                matched = ctx.clone.attentions.match(ctx, *intentions)
                params = matched.result
        wrapper = OnAttend if self.attend else OnIntend
        event = wrapper(this, params, self.fr)
        return CtxTool.fire_event(ctx, event)

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
        task = CtxTool.fetch_task_by_thought(ctx, self.this, or_create=True)
        if not task.forward():
            return OpFinish(self.this)
        ctx.clone.runtime.store_task(task)
        self.this = CtxTool.merge_thought_from_task(self.this, task)
        return None

    def _save_change(self, ctx: "Context") -> None:
        return None

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
        if task.tid == process.root:
            # 根节点结束.
            return
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
        clone = ctx.clone
        runtime = clone.runtime
        process = runtime.current_process()
        if process.root == self.this.tid:
            return self._finish_root(ctx)

        # 让调度来解决后续问题.
        # 回调到 blocking, 然后是 waiting.
        this_uml = CtxTool.thought_to_uml(self.this)
        return OpSchedule(this_uml)

    def _finish_root(self, ctx: Context):
        clone = ctx.clone
        runtime = clone.runtime
        process = runtime.current_process()
        process.quit()
        runtime.store_process(process)
        if process.parent_id:
            result = CtxTool.task_result(ctx, process.root_task)
            clone.async_input(result, )
        return None

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

    def __init__(self, this: Thought, reason: Any | None, fr: Optional[UML] = None):
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
        task = ctx.clone.runtime.fetch_task(canceling_id, False)
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

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        process = ctx.clone.runtime.current_process()
        task = process.root_task
        thought = CtxTool.fetch_thought_by_task(ctx, task)
        event = OnStart(thought)
        return CtxTool.fire_event(ctx, event)

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        pass


class OpYieldTo(AbsOperator):

    def __init__(self, this: Thought, to: UML, pid: str | None):
        self.this = this
        self.to = to
        self.pid = pid

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        """
        depend 事件可以被终止.
        """
        target_task = CtxTool.fetch_task(ctx, self.to, or_create=False)
        if not target_task:
            return None

        # 目标任务已经完成的情况.
        if target_task.status == TaskStatus.FINISHED:
            #  目标任务已经完成的话, 直接回调.
            target = CtxTool.fetch_thought_by_task(ctx, target_task)
            return OpCallback(self.this, target)
        return None

    def _save_change(self, ctx: "Context") -> None:
        task = CtxTool.fetch_task_by_thought(ctx, self.this)
        task.status = TaskStatus.YIELDING
        target_id = CtxTool.new_tid(ctx, self.to)
        task.depending = target_id
        runtime = ctx.clone.runtime
        runtime.store_task(task)
        process = runtime.current_process()

        # 创建并保存异步进程.
        target_task = CtxTool.fetch_task(ctx, self.to, or_create=True)
        sub_process = process.new_process(process.sid, target_task, self.pid, process.pid)
        runtime.store_process(sub_process)

        # 发送异步消息.
        ctx.send(self.this).async_input(
            Payload.Action("start"),
            sub_process.pid
        )
        return

    def _fire_event(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _next(self, ctx: "Context") -> Optional["Operator"]:
        uml = CtxTool.thought_to_uml(self.this)
        return OpSchedule(uml)

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

    @abstractmethod
    def intend_to(self, uml: UML, params: Dict | None = None) -> "Operator":
        try:
            this_uml = CtxTool.thought_to_uml(self.this)
            return OpIntendTo(uml, params, this_uml, attend=False)
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
        try:
            return OpYieldTo(self.this, to, pid)
        finally:
            self.destroy()
