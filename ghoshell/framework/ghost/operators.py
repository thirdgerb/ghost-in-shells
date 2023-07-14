from abc import ABCMeta, abstractmethod
from typing import Optional, List, ClassVar, Type, Dict

from ghoshell.ghost import Attention, Intention
from ghoshell.ghost import Context
from ghoshell.ghost import CtxTool
from ghoshell.ghost import OnReceived, OnActivating, OnPreempted, OnCallback
from ghoshell.ghost import OnWithdrawing, OnCanceling, OnFailing, OnQuiting
from ghoshell.ghost import Operator
from ghoshell.ghost import RuntimeTool
from ghoshell.ghost import Task, TaskStatus, TaskLevel
from ghoshell.messages import Tasked, Signal
from ghoshell.url import URL


class AbsOperator(Operator, metaclass=ABCMeta):
    """
    operator 基类. 没有提供有用的方法, 只是提供一个开发范式
    方便开发者建立思路, 划分边界.
    """

    def __init__(self, fr: URL | None = None):
        self.fr = fr

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
        # except GhostException as e:
        #     raise e
        # except Exception as e:
        #     raise

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

    def __repr__(self):
        return f"`{self.__class__.__name__} from {self.fr}: \n{self._desc()}`"

    def _desc(self) -> str:
        lines = []
        for key in self.__dict__:
            lines.append(f"{key}:{self.__dict__[key]}")
        return "\n".join(lines)


class ChainOperator(Operator):
    """
    链式 operator
    """

    def __init__(self, chain: List[Operator] = None):
        if chain is None:
            chain = []
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
        chain.insert(0, after)
        return ChainOperator(chain)

    def destroy(self) -> None:
        del self.chain

    def __repr__(self):
        result = [f"{self.__class__.__name__}:"]
        for op in self.chain:
            result.append(str(op))
        return "\n".join(result)


class ReceiveInputOperator(AbsOperator):
    """
    接受到一个 Input
    """

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        process = ctx.runtime.current_process()
        tasked = ctx.read(Tasked)

        # root 如果没有初始化, 需要执行初始化根节点.
        if not process.root:
            if ctx.input.url is not None:
                # input 传入场景信息.
                root_url = ctx.input.url.copy_with()
                root = RuntimeTool.new_task(ctx, root_url)
            elif tasked is not None:
                # 任务消息就是根节点.
                root = RuntimeTool.new_task(
                    ctx,
                    URL.new(think=tasked.think, stage="", args=tasked.args),
                )
            else:
                # 否则 root 用默认方式生成.
                root = RuntimeTool.new_task(ctx, ctx.clone.root)
            RuntimeTool.store_task(ctx, root)
            # 保存变更. 这一步理论上不是必须的.
            ctx.runtime.store_process(process)

        if tasked is not None:
            # tasked 的情况, 只需要执行 tasked 的任务就可以了.
            # 这是一种特殊的消息, 通常是内部的消息.
            return TaskedMessageOperator(tasked)

        # 正常情况下, 要判断是不是 new
        # 如果是 new 的话, 要初始化根节点.
        if process.is_new:
            # 保证不再是 new 了.
            process.add_round()
            ctx.runtime.store_process(process)
            root_task = RuntimeTool.fetch_root_task(ctx)
            # 必须先激活根节点, 然后让它进入某个状态后, 开始 receive input.
            # todo: 激活的过程是否要
            return ChainOperator([ActivateOperator(root_task.url, None, root_task.tid), ReceiveInputOperator(None)])
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:

        # 如果 payload tid 存在, 则消息希望命中目标任务. 需要调整任务的优先顺序.
        self._check_payload_tid(ctx)

        awaiting_task = RuntimeTool.fetch_current_task(ctx)

        # 目前认为需要分批匹配意图. 第一批是前序意图, 决定重定向方向.
        attentions = CtxTool.context_attentions(ctx)
        matched = CtxTool.match_attentions(ctx, attentions)

        if matched is not None:
            return IntendingOperator(matched)

        # 第二批是后续意图, 用来激活后续任务
        attentions = CtxTool.context_attentions(ctx)
        matched = CtxTool.match_attentions(ctx, attentions)
        if matched is not None:
            # 允许定义拦截逻辑.
            return IntendingOperator(matched)

        # 都没有匹配, 就尝试模糊匹配.
        if awaiting_task.level == TaskLevel.LEVEL_PUBLIC:
            matched = CtxTool.match_global_intentions(ctx)
            if matched is not None:
                return IntendingOperator(matched)

        #  所有意图匹配逻辑都没有命中, 往后走.
        return None

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return UnhandledInputOperator(None)

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
        process = ctx.runtime.current_process()
        process.set_current(target_task.tid)
        ctx.runtime.store_process(process)
        return

    def destroy(self) -> None:
        del self.fr

    def _desc(self) -> str:
        return ""


class IntendingOperator(AbsOperator):
    """
    匹配到了意图并且执行跳转.
    """

    def __init__(self, matched: Intention):
        self.matched = matched
        super().__init__(None)

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return self.matched.action(ctx)

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        if self.matched.target is None:
            return None
        target = self.matched.target
        task = RuntimeTool.fetch_task_by_url(ctx, target, False)
        if task is None:
            if target.stage:
                # 不允许前往一个新任务的内部节点.
                return None
            # 初始化一个新任务.
            return self._match_new_thought(target, self.matched.params)
        return self._intend_to_stage(ctx, task)

    def _intend_to_stage(self, ctx: "Context", task: Task) -> Optional["Operator"]:
        fr = self.matched.target
        stage_resolver = CtxTool.force_fetch_stage(ctx, fr.think, fr.stage)
        reaction_name = self.matched.reaction
        reactions = stage_resolver.reactions()
        if reaction_name is None or reaction_name not in reactions:
            return None
        reaction = reactions[reaction_name]

        thought = RuntimeTool.fetch_thought_by_task(ctx, task)
        # 这里就反映出 python 弱约束 + 强类型的痛苦了.
        result = self.matched.model_dump(include={"params"})
        op = reaction.react(ctx, thought, result.get("params", None))
        RuntimeTool.merge_thought_to_task(thought, task)
        RuntimeTool.store_task(ctx, task)
        return op

    def _match_new_thought(self, target: URL, args: Dict | None) -> Optional["Operator"]:
        if target.stage:
            return None
        target = target.copy_with(args=args)
        # 启动目标任务.
        return ActivateOperator(target, None, None)

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return UnhandledInputOperator(None)

    def destroy(self) -> None:
        del self.matched
        del self.fr

    def _desc(self) -> str:
        return f"matched:{self.matched}"


class TaskedMessageOperator(AbsOperator):
    """
    响应以传输的任务数据为消息的请求.
    """

    def __init__(self, tasked: Tasked):
        self.tasked = tasked
        super().__init__(None)

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        tasked = self.tasked
        url = URL(think=tasked.think, stage=tasked.stage, args=tasked.args.copy())
        task = RuntimeTool.fetch_task_by_url(ctx, url, True)
        # 保存任务的状态
        task.merge_tasked(tasked)
        RuntimeTool.store_task(ctx, task)
        # 进入到下一个状态.
        match task.status:
            case TaskStatus.DEAD:
                return CancelOperator(task.tid, tasked.stage)
            case TaskStatus.WAITING:
                return AwaitOperator(task.tid, tasked.stage, None, None, self.fr)
            case TaskStatus.FINISHED:
                return FinishOperator(task.tid, task.url.stage, self.fr)
            case _:
                return ForwardOperator(task.tid, list(tasked.stage), self.fr)

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        # 什么也不干.
        return RewindOperator()

    def destroy(self) -> None:
        del self.tasked
        del self.fr

    def _desc(self) -> str:
        return f"tasked:{self.tasked}"


class ActivateOperator(AbsOperator):

    def __init__(self, to: URL, fr: URL | None, target_tid: str | None):
        self.to = to
        self.target_tid = target_tid
        super().__init__(fr)

    def _desc(self) -> str:
        return f"to:{self.to}\nfr:{self.fr}\ntid:{self.target_tid}"

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        if self.target_tid:
            task = RuntimeTool.force_fetch_task(ctx, self.target_tid)
        else:
            task = RuntimeTool.fetch_task_by_url(ctx, self.to, True)
        match task.status:
            case TaskStatus.NEW:
                # think = CtxTool.force_fetch_think(ctx, self.to.think)
                # if think.is_async():
                #     # 设置 task 为 yielding, 保留了一个指针.
                #     task.status = TaskStatus.YIELDING
                #     RuntimeTool.store_task(ctx, task)
                #     # 发送异步消息, 新开一个子进程.
                #     ctx.send(None).async_input(task.to_tasked())
                #     # 正常回调任务, 当前任务已经 yielding.
                #     return ScheduleOperator()
                # 保证至少是 Running 状态.
                task.status = TaskStatus.RUNNING
                RuntimeTool.store_task(ctx, task)

                event = OnActivating(task.tid, self.to.stage, self.fr)
                return RuntimeTool.fire_event(ctx, event)
            case [TaskStatus.FINISHED, TaskStatus.DEAD]:
                # 重启任务.
                task.restart()
                RuntimeTool.store_task(ctx, task)
                event = OnActivating(task.tid, self.to.stage, self.fr)
                return RuntimeTool.fire_event(ctx, event)

            # preempting
            case [TaskStatus.PREEMPTING, TaskStatus.DEPENDING, TaskStatus.YIELDING]:
                event = OnPreempted(task.tid, task.url.stage, self.fr)
                return RuntimeTool.fire_event(ctx, event)
            case _:
                event = OnActivating(task.tid, self.to.stage, self.fr)
                return RuntimeTool.fire_event(ctx, event)

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        # 启动了目标节点, 但没有发生任何事件?
        return None

    def destroy(self) -> None:
        del self.to
        del self.fr
        del self.target_tid


class RewindOperator(AbsOperator):

    def __init__(self, repeat: bool = False, fr: URL | None = None):
        self.repeat = repeat
        super().__init__(fr)

    def _desc(self) -> str:
        return f"repeat:{self.repeat}"

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        process = ctx.runtime.current_process()
        if process.round > 2:
            ctx.runtime.rewind()
        if self.repeat:
            return AwaitOperator(None, None, None, None, self.fr)
        return None

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.repeat
        del self.fr


class AwaitOperator(AbsOperator):

    def __init__(
            self,
            tid: str | None,
            stage: str | None,
            only: List[str] | None,
            exclude: List[str] | None,
            fr: URL | None = None,
            to: URL | None = None,
    ):
        self.tid = tid
        self.stage = stage
        self.only = only
        self.exclude = exclude
        self.to = to
        super().__init__(fr)

    def _desc(self) -> str:
        return f"tid:{self.tid}\nstage:{self.stage}\nonly:{self.only}\nexclude:{self.exclude}"

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        tid = self.tid
        runtime = ctx.runtime
        process = runtime.current_process()
        # 变更 awaiting 任务.
        if tid is not None:
            process.current = tid
        runtime.store_process(process)

        task = RuntimeTool.fetch_task(ctx, tid)
        # 获取 intentions
        stage = CtxTool.force_fetch_stage(ctx, task.url.think, task.url.stage)

        reactions = stage.reactions()
        reaction_names = set(reactions.keys())
        if len(reaction_names) == 0:
            pass
        elif self.only is not None:
            reaction_names = reaction_names & set(self.only)
        elif self.exclude is not None:
            reaction_names = reaction_names - set(self.exclude)

        attentions = []
        for reaction_name in reaction_names:
            reaction = reactions.get(reaction_name, None)
            if reaction is None:
                continue
            intentions = reaction.intentions(ctx)
            url_dict = task.url.model_dump()
            attention = Attention(
                to=url_dict,
                intentions=[intention.model_dump() for intention in intentions],
                reaction=reaction_name,
                level=reaction.level(),
            )
            attentions.append(attention)
        task.await_at(self.stage, attentions)
        # 变更 process 的 awaiting
        process.current = task.tid
        RuntimeTool.store_task(ctx, task)
        RuntimeTool.store_process(ctx, process)
        # 任务结束.
        return None

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        if self.to is not None:
            return ActivateOperator(self.to, self.fr, None)
        return None

    def destroy(self) -> None:
        del self.tid
        del self.exclude
        del self.stage
        del self.only
        del self.fr
        del self.to


class ForwardOperator(AbsOperator):
    """
    让当前任务向前运行.
    """

    def __init__(self, tid: str, stages: List[str], fr: URL | None = None):
        self.tid = tid
        self.stages = stages
        super().__init__(fr)

    def _desc(self) -> str:
        return f"tid:{self.tid}\nstages:{self.stages}"

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        # 状态变更.
        task = RuntimeTool.fetch_task(ctx, self.tid)
        if len(self.stages) > 0:
            task.insert(self.stages)
            RuntimeTool.store_task(ctx, task)

        task = RuntimeTool.fetch_task(ctx, self.tid)
        _next = task.forward()
        RuntimeTool.store_task(ctx, task)
        if _next is not None:
            # 启动目标节点.
            return ActivateOperator(task.url.copy_with(stage=_next), task.url, task.tid)
        # 结束当前 task, 就在当前位置.
        return FinishOperator(task.tid, task.url.stage, self.fr)

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.tid
        del self.stages
        del self.fr


class FinishOperator(AbsOperator):
    def __init__(self, tid: str, stage: str, fr: URL | None = None):
        self.tid = tid
        self.stage = stage
        super().__init__(fr)

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        # 变更状态
        task = RuntimeTool.fetch_task(ctx, self.tid)
        # 更新状态.
        callbacks = task.done(TaskStatus.FINISHED, self.stage)
        # 没有回调节点.
        if not callbacks:
            return None

        tasks = RuntimeTool.fetch_process_tasks_by_ids(ctx, list(callbacks))
        # 遍历所有依赖当前任务的那些任务.
        preempting = []
        for ptr in tasks:
            # depending 任务调整为 blocking 任务
            ptr.status = TaskStatus.PREEMPTING
            preempting.append(ptr)

        # 只保存 runtime 变更, 不涉及 data.
        RuntimeTool.store_task(ctx, *preempting)
        return None

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return ScheduleOperator()

    def destroy(self) -> None:
        del self.tid
        del self.stage
        del self.fr


class UnhandledInputOperator(AbsOperator):

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        pass

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        awaiting_task = RuntimeTool.fetch_current_task(ctx)
        #  让 current 对话任务来做兜底
        after = self._task_on_received(ctx, awaiting_task)
        if after is not None:
            return after
        # 让 root 级别的对话任务来做兜底.
        # 不再 fallback 到 root 上.
        # root_task = RuntimeTool.fetch_root_task(ctx)
        # if root_task.tid == awaiting_task.tid:
        #     return None
        #
        # after = self._fallback_to_task(ctx, root_task)
        # if after is not None:
        #     return after
        return None

    @classmethod
    def _task_on_received(cls, ctx: "Context", task: Task) -> Optional[Operator]:
        # 当前任务.  fallback
        event = OnReceived(task.tid, task.url.stage, None)
        op = RuntimeTool.fire_event(ctx, event)
        return op

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        # 装作没听懂.
        return RewindOperator(repeat=False)

    def destroy(self) -> None:
        return


class WithdrawOperator(AbsOperator, metaclass=ABCMeta):
    """
    """
    status: ClassVar[int]
    wrapper: Type[OnWithdrawing]

    def __init__(
            self,
            tid: str,
            at_stage: str | None,
            fr: URL | None = None
    ):
        self.tid = tid
        self.at_stage = at_stage
        super().__init__(fr)

    def _intercept(self, ctx: Context) -> Optional[Operator]:
        # 检查流程是否被拦截
        current_task = RuntimeTool.fetch_task(ctx, self.tid)
        # 退出.
        if current_task is None:
            return None
        # only working task's canceling can be intercepted
        if not TaskStatus.is_working(current_task.status):
            return None
        if current_task.status == self.status:
            return None

        # 可能是一个 None
        event = self.wrapper(current_task.tid, current_task.url.stage, None)
        # 如果没有被拦截, 就继续往后走.
        return RuntimeTool.fire_event(ctx, event)

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        current_task = RuntimeTool.fetch_task(ctx, self.tid)
        if current_task is None:
            # 继续走后续的取消流程.
            # 没有链式取消了.
            return None

        callbacks = current_task.done(TaskStatus.DEAD, self.at_stage)
        RuntimeTool.store_task(ctx, current_task)
        # 保存变更.
        if not callbacks:
            return None

        # 检查 callbacks
        callback_tasks = RuntimeTool.fetch_process_tasks_by_ids(ctx, list(callbacks))
        for task in callback_tasks:
            task.status = self.status
        RuntimeTool.store_task(*callback_tasks)
        # 正常情况才走 schedule
        p = ctx.runtime.current_process()
        p.reset_indexes()
        return None

    def _fallback(self, ctx: Context) -> Optional[Operator]:
        return ScheduleOperator()

    def destroy(self) -> None:
        del self.tid
        del self.fr


class CancelOperator(WithdrawOperator):
    status = TaskStatus.CANCELING
    wrapper = OnCanceling


class FailOperator(WithdrawOperator):
    status = TaskStatus.FAILING
    wrapper = OnFailing


class QuitOperator(WithdrawOperator):
    status = TaskStatus.CANCELING
    wrapper = OnQuiting

    def _intercept(self, ctx: Context) -> Optional[Operator]:
        intercepted = super()._intercept(ctx)
        if intercepted:
            RuntimeTool.set_quiting(ctx, False)
        return intercepted

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        after = super()._run_operation(ctx)
        RuntimeTool.set_quiting(ctx, True)
        return after


class ScheduleOperator(AbsOperator):

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        runtime = ctx.runtime
        process = runtime.current_process()

        fallback = process.fallback()
        if fallback is not None and fallback.tid != process.root:
            tid = fallback.tid
            # 退出过程中, 调度会退出每一个中间任务.
            if process.quiting:
                return QuitOperator(tid, None)
            else:
                match fallback.status:
                    case TaskStatus.CANCELING:
                        return CancelOperator(tid, None)
                    case TaskStatus.FAILING:
                        return FailOperator(tid, None)
                    case TaskStatus.RUNNING:
                        return ForwardOperator(tid, [], self.fr)
                    case _:
                        return self._preempt(ctx, tid)

        root = RuntimeTool.fetch_root_task(ctx)
        if TaskStatus.is_working(root.status):
            # 重新回到根节点.
            return self._preempt(ctx, process.root)

        if TaskStatus.is_final(root.status):
            # 如果有父进程, 就回调父进程.
            if process.parent_id:
                ctx.send_at(None).async_input(root.to_tasked(), process_id=process.parent_id, trace=None)

        # quit 流程
        process = ctx.runtime.current_process()
        process.quiting = True
        ctx.send_at(None).output(Signal.quit())
        return None

    @classmethod
    def _preempt(cls, ctx: Context, tid: str) -> Optional[Operator]:
        process = ctx.runtime.current_process()
        process.set_current(tid)
        RuntimeTool.store_process(ctx, process)
        # 触发事件.
        task = RuntimeTool.fetch_task(ctx, tid)
        event = OnPreempted(task.tid, task.url.stage, None)
        return RuntimeTool.fire_event(ctx, event)

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        return None


class ResetOperator(AbsOperator):
    """
    重置进程
    """

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        runtime = ctx.runtime
        process = runtime.current_process()
        process.reset()
        runtime.store_process(process)

        task = RuntimeTool.fetch_root_task(ctx)
        event = OnActivating(task.tid, task.url.stage, None)
        return RuntimeTool.fire_event(ctx, event)

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.fr


class OpRestart(AbsOperator):

    def __init__(self, tid: str, fr: URL | None = None):
        self.tid = tid
        super().__init__(fr)

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        task = RuntimeTool.force_fetch_task(ctx, self.tid)
        task.restart()
        RuntimeTool.store_task(ctx, task)
        return ActivateOperator(task.url, None, task.tid)

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.tid
        del self.fr


class DependOnOperator(AbsOperator):

    def __init__(self, tid: str, stage: str, target: URL, fr: URL):
        self.stage = stage
        self.tid = tid
        self.target = target
        super().__init__(fr)

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        """
        depend 事件可以被终止.
        """
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        self_task = RuntimeTool.force_fetch_task(ctx, self.tid)
        target_task = RuntimeTool.fetch_task_by_url(ctx, self.target, create=True)

        match target_task.status:
            case TaskStatus.FINISHED:
                # callback 事件
                result = RuntimeTool.task_result(ctx, target_task)
                event = OnCallback(self_task.tid, self_task.url.stage, target_task.url.copy_with(), result)
                return RuntimeTool.fire_event(ctx, event)
            case TaskStatus.DEAD:
                # cancel 事件
                return CancelOperator(self.tid, None)
            case _:
                target_task.add_callback(self.tid)
                self_task.depend(self.stage)
                RuntimeTool.store_task(ctx, target_task, self_task)
                return ActivateOperator(target_task.url, self_task.url, target_task.tid)

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.tid
        del self.stage
        del self.target
        del self.fr


class RestartOperator(AbsOperator):

    def __init__(self, tid: str, fr: URL | None = None):
        self.tid = tid
        super().__init__(fr)

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        task = RuntimeTool.force_fetch_task(ctx, self.tid)
        if task.status != TaskStatus.NEW:
            task.restart()
            RuntimeTool.store_task(ctx, task)
        return ActivateOperator(task.url, None, task.tid)

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def destroy(self) -> None:
        del self.tid
        del self.fr


class YieldToOperator(AbsOperator):

    def __init__(self, tid: str, stage: str, is_callback: bool, fr: URL | None = None):
        self.tid = tid
        self.stage = stage
        self.is_callback = is_callback
        super().__init__(fr)

    def _intercept(self, ctx: "Context") -> Optional["Operator"]:
        return None

    def _run_operation(self, ctx: "Context") -> Optional["Operator"]:
        task = RuntimeTool.force_fetch_task(ctx, self.tid)
        tasked = task.to_tasked()
        tasked.stage = self.stage
        if self.is_callback:
            parent_id = ctx.runtime.current_process().parent_id
            # 无法回调, 当成同步请求运行.
            if parent_id is None:
                return ForwardOperator(task.tid, [self.stage], self.fr)

            # 发送异步消息.
            thought = RuntimeTool.fetch_thought_by_task(ctx, task)
            ctx.send_at(thought).async_input(tasked, process_id=parent_id)
            # 直接进入回收状态.
            task.status = TaskStatus.DEAD
        else:
            thought = RuntimeTool.fetch_thought_by_task(ctx, task)
            ctx.send_at(thought).async_input(tasked)
            # 变更自身状态.
            task.status = TaskStatus.YIELDING
        RuntimeTool.store_task(ctx, task)
        return None

    def _fallback(self, ctx: "Context") -> Optional["Operator"]:
        return ScheduleOperator()

    def destroy(self) -> None:
        del self.tid
        del self.stage
        del self.is_callback
        del self.fr
