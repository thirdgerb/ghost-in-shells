from typing import Optional, Dict, List, Any, Tuple

from ghoshell.ghost import Context, CtxTool, UML, Process, IntentionMeta, Event
from ghoshell.ghost import MissUnderstoodException
from ghoshell.ghost import OnFallback, OnIntend, OnRedirect, OnRepeat
from ghoshell.ghost import Operator, Operate
from ghoshell.ghost import Task, TaskPtr, TaskStatus, TaskLevel
from ghoshell.ghost import Thought


def fire_event(ctx: "Context", event: Event) -> Optional[Operator]:
    stage = CtxTool.stage(ctx, event.this.uml)
    return stage.on_event(ctx, event)


class OpReceiveInput(Operator):
    """
    接受到一个 Input, 启动默认的处理流程.
    会根据 root -> current 任务生成一个意图树
    """

    def run(self, ctx: "Context") -> Optional[Operator]:
        runtime = ctx.runtime
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
        current_task = process.task_ptrs.get(process.current)
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
        current_task = process.task_ptrs.get(process.current)
        if current_task.level != TaskLevel.LEVEL_PUBLIC:
            return None
        attentions = ctx.attentions
        matched = attentions.wildcard_match(ctx)
        if matched is not None:
            return OpReceiveInput.Matched(matched, None)
        return None

    @classmethod
    def attention_metas(cls, ctx: "Context", process: Process, current_task: TaskPtr) -> Dict[str, List[IntentionMeta]]:
        """
        从进程中获取当前匹配的意图.
        """
        result: Dict[str, List[IntentionMeta]] = {}
        # 第一步, 添加 root
        root_ptr = process.task_ptrs.get(process.root)
        cls._add_intention_meta_to_attentions(ctx, result, root_ptr)

        if process.current != root_ptr:
            cls._add_intention_meta_to_attentions(ctx, result, current_task)

        # 封闭域任务, 不再继续增加注意目标.
        if current_task.level <= TaskLevel.LEVEL_PRIVATE:
            return result

        # 第三步, 添加 waiting 中的节点的意图.
        for tid in process.waiting:
            blocking = process.task_ptrs.get(tid)
            cls._add_intention_meta_to_attentions(ctx, result, blocking)
        return result

    @classmethod
    def _add_intention_meta_to_attentions(
            cls,
            ctx: Context,
            result: Dict[str, List[IntentionMeta]],
            task_ptr: TaskPtr,
    ) -> Dict[str, List[IntentionMeta]]:
        # 初始化
        # 上下文中生成意图树.
        for uml in task_ptr.attentions:
            stage = CtxTool.stage(ctx, uml)
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
    接受到了一个异步的回调.
    """

    def __init__(self, callback_task_id: str):
        self.callback_task_id = callback_task_id

    def run(self, ctx: "Context") -> Optional[Operator]:
        return None

    def destroy(self) -> None:
        del self.callback_task_id


class OpFallback(Operator):
    """
    没有任何意图被匹配到时.
    """

    def run(self, ctx: "Context") -> Optional[Operator]:
        process = ctx.runtime.current_process()
        #  让 current 对话任务来做兜底
        forward = self.fallback_to_current(ctx, process)
        if forward is not None:
            return forward
        # 让 root 级别的对话任务来做兜底.
        forward = self.fallback_to_root(ctx, process)
        if forward is not None:
            return forward

        # 无法处理的输入消息, 返回错误.
        # todo: fulfill exception details
        raise MissUnderstoodException()

    @staticmethod
    def fallback_to_current(ctx: "Context", process: Process) -> Optional[Operator]:
        # 当前任务.  fallback
        current_task_ptr = process.current_task()
        current_thought = ctx.thought(current_task_ptr.uml)
        event = OnFallback(current_thought)
        return fire_event(ctx, event)

    @staticmethod
    def fallback_to_root(ctx: "Context", process: Process) -> Optional[Operator]:
        # root 任务 fallback
        if process.current == process.root:
            return None
        root_ptr = process.current_task()
        root_thought = ctx.thought(root_ptr.uml)
        event = OnFallback(root_thought)
        return fire_event(ctx, event)

    def destroy(self) -> None:
        pass


class OpAttendTo(Operator):
    def __init__(self, to: UML, args: Optional[Dict]):
        self.to = to
        self.args = args

    def run(self, ctx: "Context") -> Optional[Operator]:
        pass

    def destroy(self) -> None:
        del self.to
        del self.args


class OpIntentTo(Operator):
    """
    命中了一个意图, 前往目标任务.
    过程中生产一个事件, 如果没问题的话就正式激活目标任务.
    """

    def __init__(self, to: Task, args: Optional[Dict] = None):
        # 匹配的目标
        self.to: Task = to
        # 匹配的参数, 如果为 none 的话还需要二次检查.
        self.args: Optional[Dict] = args

    def run(self, ctx: "Context") -> Optional[Operator]:
        process = ctx.runtime.current_process()
        current_task = process.current_task()
        to_thought = ctx.thought(self.to)

        if self.args is None:
            # 用 intention 重新匹配一次.
            stage = CtxTool.stage(ctx, to_thought.uml)
            self.args = stage.intention(ctx).match(ctx)

        # 意图命中了自身.
        event = OnIntend(to_thought, self.args, current_task.uml)
        return fire_event(ctx, event)

        # 如果不是新建的任务
        if to_thought.status != TaskStatus.TASK_NEW:
            event = OnIntend(to_thought)
            # 是否任务被拦截.
            interceptor = AbsOperator.fire_event(ctx, event)
            if interceptor is not None:
                return interceptor

    @staticmethod
    def on_intercept(ctx: "Context", process: Process) -> Optional[Operator]:
        current_task_ptr = process.task_ptrs.get(process.current)
        current_thought = ctx.thought(current_task_ptr.uml)
        event = Event(current_thought, Event.ON_INTERCEPT)

    def on_intend_to(self):
        pass

    def destroy(self) -> None:
        pass


class OpGoStage(Operator):

    def __init__(self, thought: Thought, *stages: str):
        self.this: Thought = thought
        self.forwards: Tuple = stages

    def run(self, ctx: "Context") -> Optional[Operator]:
        task = CtxTool.thought_to_task(ctx, self.this)
        # 将 stages 插入到前面.
        if len(self.forwards) > 0:
            task.add_stages(*self.forwards)
        # 执行 forward 任务.
        ctx.runtime.store_task(task)
        return OpForwardStage(self.this)

    def destroy(self) -> None:
        del self.this
        del self.forwards


class OpForwardStage(Operator):

    def __init__(self, this: Thought):
        self.this = this

    def run(self, ctx: "Context") -> Optional[Operator]:
        this = self.this
        fr = this.uml
        task = CtxTool.thought_to_task(ctx, this)
        success = task.forward()
        # 记得要保存.
        ctx.runtime.store_task(task)

        if not success:
            # 没有后续任务, 执行 finish
            return OpFinish(self.this)
        # 有后续任务, 则启动它.
        self.this.from_task(task)
        # 触发事件, 等待事件提供的后续流程.
        event = OnRedirect(this, fr)
        return fire_event(ctx, event)

    def destroy(self) -> None:
        del self.this


class OpFinish(Operator):
    def __init__(self, this: Thought):
        self.this = this

    def run(self, ctx: "Context") -> Optional[Operator]:
        # 变更状态
        this = self.this
        this.status = TaskStatus.TASK_FINISHED
        task = CtxTool.thought_to_task(ctx, this)
        # 保存任务.
        runtime = ctx.runtime
        depending = task.depending
        runtime.store_task(task)

        process = runtime.current_process()
        blocking = []
        for depending_tid in depending:
            ptr = process.task_ptrs.get(depending_tid, None)
            if ptr is None:
                continue
            ptr.status = TaskStatus.TASK_BLOCKING
            blocking.append(ptr)
        runtime.store_task_ptrs(*blocking)
        # 让调度来解决后续问题.
        # 回调到 blocking, 然后是 waiting.
        return OpSchedule()

    def destroy(self) -> None:
        del self.this


class OpSchedule(Operator):
    pass


class OpWait(Operator):

    def __init__(self, this: Thought):
        self.this: Thought = this

    def run(self, ctx: "Context") -> Optional[Operator]:
        runtime = ctx.runtime
        process = runtime.current_process()
        current_task = runtime.fetch_task(process.current)
        wait_task = CtxTool.thought_to_task(ctx, self.this)

        if wait_task.tid != current_task.tid:
            current_task.status = TaskStatus.TASK_WAITING
            wait_task.status = TaskStatus.TASK_AWAIT
            # 两个 task 的状态都变更了.
            runtime.store_task(wait_task, current_task)
        else:
            runtime.store_task(wait_task)
        return None

    def destroy(self) -> None:
        del self.this


class OpRepeat(Operator):

    def __init__(self, this: Thought):
        self.this = this

    def run(self, ctx: "Context") -> Optional[Operator]:
        runtime = ctx.runtime
        process = runtime.current_process()
        current_task = runtime.fetch_task(process.current)
        thought = CtxTool.task_to_thought(ctx, current_task)
        # 重新启动当前任务.
        event = OnRepeat(thought, self.this.uml)
        return fire_event(ctx, event)

    def destroy(self) -> None:
        del self.this


class OpRewind(Operator):
    def run(self, ctx: "Context") -> Optional[Operator]:
        ctx.runtime.rewind()
        return None

    def destroy(self) -> None:
        pass


class OperateImpl(Operate):
    def __init__(self, ctx: Context, this: Thought):
        self.ctx = ctx
        self.this = this

    def _destroy(self) -> None:
        del self.ctx
        del self.this

    def go_stage(self, *stages: str) -> Operator:
        try:
            op = OpGoStage(self.this, *stages)
            return op
        finally:
            self._destroy()

    def repeat(self) -> Operator:
        try:
            return OpRepeat(self.this)
        finally:
            self._destroy()

    def rewind(self) -> Operator:
        try:
            return OpRewind()
        finally:
            self._destroy()

    def restart(self) -> Operator:
        pass

    def wait(self) -> Operator:
        try:
            return OpWait(self.this)
        finally:
            self._destroy()

    def forward(self) -> Operator:
        try:
            return OpForwardStage(self.this)
        finally:
            self._destroy()

    def finish(self) -> Operator:
        try:
            return OpFinish(self.this)
        finally:
            self._destroy()

    def cancel(self, reason: Optional[Any]) -> Operator:
        pass

    def quit(self, reason: Optional[Any]) -> Operator:
        pass

    def fail(self, reason: Optional[Any]) -> Operator:
        pass
