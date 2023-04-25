from __future__ import annotations

from typing import Optional, Dict, List, Tuple

from ghoshell.ghost.context import Context
from ghoshell.ghost.exceptions import MindsetNotFoundException, RuntimeException
from ghoshell.ghost.mindset import Think, Thought, Stage, Event
from ghoshell.ghost.mindset.focus import Intention, Attention
from ghoshell.ghost.mindset.operator import Operator
from ghoshell.ghost.runtime import Task, TaskStatus, Process, TaskLevel
from ghoshell.ghost.url import URL

GroupedIntentions = Dict[str, List[Intention]]


class CtxTool:
    """
    基于抽象实现的一些基础上下文工具.
    上下文是面向开发者的用户态操作, 操作的主体是 Stage, 操作的对象是 Event, url 和 Thought
    而 task 是 runtime 操作的对象, 两者应该严格隔离开, 否则调度流程会极不清晰
    因此有 CtxTool 和 RuntimeTool 两种.
    """

    @classmethod
    def fetch_thought(cls, ctx: "Context", url: URL) -> Thought:
        task = RuntimeTool.fetch_task_by_url(ctx, url, True)
        return RuntimeTool.fetch_thought_by_task(ctx, task)

    @classmethod
    def fetch_think_result(cls, ctx: "Context", url: URL) -> Tuple[bool, Optional[Dict]]:
        task = RuntimeTool.fetch_task_by_url(ctx, url, False)
        # 目标任务未初始化.
        if task is None:
            return False, None
        # 目标任务未完成
        if task.status != TaskStatus.FINISHED:
            return False, None
        thought = RuntimeTool.fetch_thought_by_task(ctx, task)
        think = ctx.clone.mindset.force_fetch(task.url.resolver)
        return True, think.result(thought)

    #
    # @classmethod
    # def match_stage_intention(cls, ctx: "Context", think: str, stage: str) -> Optional[Intention]:
    #     """
    #     尝试匹配一个 think.stage 的意图.
    #     前提是意图存在.
    #     """
    #     stage = cls.force_fetch_stage(ctx, think, stage)
    #     metas = stage.intentions(ctx)
    #     if metas is None:
    #         return None
    #     return ctx.clone.focus.match(ctx, *metas)

    # ---- thought 相关方法 ----#

    @classmethod
    def force_fetch_stage(cls, ctx: Context, think: str, stage: str) -> "Stage":
        """
        取出一个 think.stage, 不存在要抛出异常.
        """
        stage = cls.fetch_stage(ctx, think, stage)
        if stage is None:
            raise MindsetNotFoundException("todo")
        return stage

    @classmethod
    def force_fetch_think(cls, ctx: Context, think: str) -> "Think":
        return ctx.clone.mindset.force_fetch(think)

    @classmethod
    def fetch_stage(cls, ctx: Context, think: str, stage: str) -> Optional["Stage"]:
        think = ctx.clone.mindset.fetch(think)
        stage = think.fetch_stage(stage)
        return stage

    @classmethod
    def match_attentions(
            cls,
            ctx: "Context",
            attentions: List[Attention],
    ) -> Optional[Intention]:
        """
        匹配可能的意图. 直达或者创建任务.
        """
        grouped_intentions: GroupedIntentions = {}
        # 如果当前任务是 public 级别的任务, 则允许做意图的模糊匹配.
        # 意图的模糊匹配并不精确到参数上. 需要二次加工.
        for attention in attentions:
            for intention in attention.intentions:
                # 标记索引.
                intention.target = attention.fr
                intention.reaction = attention.reaction

            grouped_intentions = cls.group_intentions(grouped_intentions, attention.intentions)
        ordered_kinds = ctx.clone.focus.kinds()
        focus = ctx.clone.focus
        for kind in ordered_kinds:
            if kind not in grouped_intentions:
                continue
            intentions = grouped_intentions[kind]
            matched = focus.match(ctx, kind, intentions)
            if matched is not None:
                return matched
        return None

    @classmethod
    def group_intentions(cls, grouped: GroupedIntentions, intentions: List[Intention]) -> GroupedIntentions:
        for intention in intentions:
            kind = intention.kind
            if kind not in grouped:
                grouped[kind] = []
            grouped[kind].append(intention)
        return grouped

    @classmethod
    def match_global_intentions(
            cls,
            ctx: "Context",
    ) -> Optional[Intention]:
        attentions = ctx.clone.attentions
        return attentions.global_match(ctx)

    # @classmethod
    # def context_fallback_intentions(cls, ctx: "Context", level: int) -> List[Attention]:
    #     """
    #     如果注意机制没有生效, 接下来走回调机制, 看看是否会激活一些已经有的任务.
    #     """
    #     runtime = ctx.runtime
    #     process = runtime.current_process()
    #     result: List[Attention] = []
    #
    #     # 当前任务是最高优的.
    #     awaiting_task = RuntimeTool.fetch_root_task(ctx)
    #     cls._add_task_intentions(ctx, result, awaiting_task, private=True, forward=False)
    #
    #     # 当前任务的状态是 protected, 才允许回溯匹配. 否则直接退出.
    #     if level != TaskLevel.LEVEL_PRIVATE:
    #         return result
    #
    #     # blocking 的任务也可以被消息来主动抢占.
    #     blocking = process.preempting
    #     for tid in blocking:
    #         blocking_task = process.get_task(tid)
    #         result = cls._add_task_intentions(ctx, result, blocking_task, private=False, forward=False)
    #
    #     # 检查 waiting, 将 waiting 都入栈.
    #     # waiting 不能包含 root 和 awaiting
    #     waiting = process.waiting
    #     for tid in waiting:
    #         waiting_task = process.get_task(tid)
    #         result = cls._add_task_intentions(ctx, result, waiting_task, private=False, forward=False)
    #
    #     # 添加 root 节点.
    #     if process.awaiting != process.root:
    #         root_task = RuntimeTool.fetch_root_task(ctx)
    #         result = cls._add_task_intentions(ctx, result, root_task, private=False, forward=False)
    #
    #     return result

    @classmethod
    def context_attentions(cls, ctx: "Context") -> List[Attention]:
        """
        上下文相关的前序意图
        可以根据这些意图, 跳转到别的节点.
        """
        runtime = ctx.runtime
        process = runtime.current_process()
        result: List[Attention] = []

        # 第一步, 添加 root. root 永远有最高优先级.
        root_task = RuntimeTool.fetch_root_task(ctx)
        # 添加 awaiting 的注意目标.
        awaiting_task = RuntimeTool.fetch_awaiting_task(ctx)
        # public, protected, private
        awaiting_task_level = awaiting_task.level

        # awaiting 永远最高优.
        if awaiting_task.tid != root_task.tid and awaiting_task.attentions is not None:
            # awaiting 添加所有.
            result.append(*awaiting_task.attentions)

        if root_task.tid != awaiting_task.tid and root_task.attentions is not None:
            for attention in root_task.attentions:
                # root 非私有方法都可以添加进去, 而且是高优.
                if attention.level != TaskLevel.LEVEL_PRIVATE:
                    result.append(*root_task.attentions)

        # 封闭域任务, 不再继续增加注意目标.
        if awaiting_task_level == TaskLevel.LEVEL_PRIVATE:
            return result

        # 第三步, 添加 waiting 中的节点的意图.
        for tid in process.waiting:
            waiting = process.get_task(tid)
            # result = cls._add_task_intentions(ctx, result, waiting, private=False, forward=True)
            if waiting is not None and waiting.attentions is not None:
                for attention in waiting.attentions:
                    # protected + public
                    # public + public
                    if TaskLevel.allow(awaiting_task_level, attention.level):
                        result.append(attention)
        return result

    @classmethod
    def current_process(cls, ctx: Context) -> Process:
        return ctx.runtime.current_process()

    @classmethod
    def _add_task_intentions(
            cls,
            ctx: Context,
            result: GroupedIntentions,
            task: Task,
            private: bool,
            forward: bool,
    ) -> GroupedIntentions:

        fr = None
        if forward:
            fr = task.url
            url_list = task.attentions
        else:
            url_list = [task.url]

        if not url_list:
            return result

        for target in url_list:
            stage = CtxTool.force_fetch_stage(ctx, target.resolver, target.stage)

            # 从 stage 里获取 intention
            intentions = stage.intentions(ctx)
            if not intentions:
                continue
            #  初始化 intentions
            for intention in intentions:
                # 添加好关联路径.
                intention.target = fr

            # 从 intentions 组装成为 GroupedIntentions
            for meta in intentions:
                # 私有意图无法在非私有场景使用.
                if meta.private and not private:
                    continue
                kind = meta.kind
                if kind not in result:
                    result[kind] = []
                result[kind].append(meta)
        return result


class RuntimeTool:
    """
    基于抽象实现的一些基础运行时工具.
    Runtime 是面向系统的多任务调度, 操作的主体是 Process, Task, Thought 等
    将调度流程和面向用户态的工具进行严格的拆分.

    关键在于, Thought 不作为中间对象来暴露, 它的存在只在 event 里实现初始化.
    """

    @classmethod
    def fire_event(cls, ctx: Context, event: Event) -> Operator | None:
        """
        基于 thought 触发一个 stage 的事件.
        """
        if event.fr is None:
            awaiting = RuntimeTool.fetch_awaiting_task(ctx)
            event.fr = awaiting.url.copy_with()

        # 用 task 的信息补完 thought
        task = cls.force_fetch_task(ctx, event.task_id)

        # 初始化 thought. 这个 thought 里应该包含正确的 tid.
        # 将变量注入到 thought.
        thought = cls.fetch_thought_by_task(ctx, task)
        thought.url.stage = event.stage

        # 触发事件. 要使用 event 的 stage
        stage = CtxTool.force_fetch_stage(ctx, thought.url.resolver, thought.url.stage)
        after = stage.on_event(ctx, thought, event)

        # 这时 thought 已经变更了, 变更的信息要保存到 task 里.
        task = RuntimeTool.merge_thought_to_task(thought, task)

        # 保存 task 变更后的状态.
        cls.store_task(ctx, task)
        # 帮助 python 做 gc 的准备工作.
        thought.destroy()
        event.destroy()
        # 返回.
        return after

    @classmethod
    def fetch_thought_by_task(cls, ctx: Context, task: Task) -> Thought:
        # 初始化 thought. 这个 thought 里应该包含正确的 tid.
        thought = cls.new_thought(ctx, task.url)
        thought = cls.merge_task_to_thought(task, thought)
        return thought

    @classmethod
    def fetch_task_by_url(cls, ctx: Context, url: URL, create: bool) -> Task:
        tid = cls.new_task_id(ctx, url)
        task = ctx.runtime.fetch_task(tid)
        if task is None and create:
            task = cls.new_task(ctx, url)
            ctx.runtime.store_task(task)
        return task

    @classmethod
    def fetch_process_tasks_by_ids(cls, ctx: Context, ids: List[str]) -> List[Task]:
        process = ctx.runtime.current_process()
        result = []
        for tid in ids:
            ptr = process.get_task(tid)
            if ptr is None:
                # 已经不被需要了.
                continue
            result.append(ptr)
        return result

    @classmethod
    def fetch_task(cls, ctx: Context, tid: str) -> Task | None:
        return ctx.runtime.fetch_task(tid)

    @classmethod
    def force_fetch_task(cls, ctx: Context, tid: str) -> Task:
        task = cls.fetch_task(ctx, tid)
        if task is None:
            # todo: todo
            raise RuntimeException("todo")
        return task

    @classmethod
    def fetch_root_task(cls, ctx: Context) -> Task:
        runtime = ctx.runtime
        process = runtime.current_process()
        task = runtime.fetch_task(process.root)
        if task is None:
            # todo
            raise RuntimeException("todo")
        return task

    @classmethod
    def fetch_awaiting_task(cls, ctx: Context) -> Task:
        runtime = ctx.runtime
        process = runtime.current_process()
        task = runtime.fetch_task(process.awaiting)
        if task is None:
            # todo
            raise RuntimeException("todo")
        return task

    @classmethod
    def new_thought(cls, ctx: Context, url: URL) -> "Thought":
        """
        根据 url 初始化一个 thought
        并没有执行实例化
        """
        think = ctx.clone.mindset.force_fetch(url.resolver)
        thought = think.new_thought(ctx, url.args)
        return thought

    @classmethod
    def merge_task_to_thought(cls, task: Task, thought: Thought) -> Thought:
        """
        """
        if task.vars is not None:
            thought.set_variables(task.vars)
        # stage 以 url 为准. 不以 task 为准. 这个 trick 还是让人不舒服.
        thought.tid = task.tid
        thought.url = task.url.copy_with()
        thought.status = task.status
        thought.level = task.level
        thought.overdue = task.overdue
        thought.priority = task.priority
        return thought

    @classmethod
    def merge_thought_to_task(cls, thought: Thought, task: Task) -> Task:
        task.vars = thought.vars()
        task.level = thought.level
        task.overdue = thought.overdue
        task.priority = thought.priority
        return task

    @classmethod
    def task_result(cls, ctx: Context, task: Task) -> Optional[Dict]:
        """
        通过 task 还原一个任务的返回值. 通常任务已经结束时才这么做.
        """
        if task.status != TaskStatus.FINISHED:
            return None
        url = task.url
        thought = cls.new_thought(ctx, url)
        thought = cls.merge_task_to_thought(task, thought)
        think = ctx.clone.mindset.force_fetch(url.resolver)
        return think.result(thought)

    @classmethod
    def new_task(cls, ctx: Context, url: URL) -> Task:
        """
        根据 url 初始化一个 task
        """
        tid = cls.new_task_id(ctx, url)
        return Task(
            tid=tid,
            resolver=url.resolver,
            stage="",
            args=url.args.copy(),
        )

    @classmethod
    def new_task_id(cls, ctx: Context, url: URL) -> str:
        # todo: 以后实现一个 ctx 级别的缓存, 避免重复生成.
        clone = ctx.clone
        mindset = clone.mindset
        think = mindset.force_fetch(url.resolver)
        tid = think.new_task_id(ctx, url.args)
        return tid

    @classmethod
    def store_task(cls, ctx: Context, *tasks: Task) -> None:
        if len(tasks) > 0:
            ctx.runtime.store_task(*tasks)

    @classmethod
    def set_quiting(cls, ctx: Context, quiting: bool) -> None:
        runtime = ctx.runtime
        process = runtime.current_process()
        process.quiting = quiting
        runtime.store_process(process)

    #
    # @classmethod
    # def fetch_task(cls, ctx: Context, url: url, or_create: bool = True) -> Optional[Task]:
    #     clone = ctx.clone
    #     mindset = clone.mind
    #     think = mindset.fetch(url.think)
    #     if think is None:
    #         return None
    #     tid = think.new_task_id(ctx, url.args)
    #     runtime = clone.runtime
    #     process = runtime.current_process()
    #     task = process.get_task(tid)
    #     if task is not None:
    #         return task
    #
    #     if think.is_long_term():
    #         task = runtime.fetch_long_term_task(tid)
    #     if task is not None:
    #         return task
    #
    #     if not or_create:
    #         return None
    #
    #     return Task(
    #         tid=tid,
    #         resolver=url.think,
    #         stage="",
    #         args=url.args.copy(),
    #     )

    # @classmethod
    # def state_msg_to_task(cls, ctx: Context, state: StateMsg) -> Task:
    #     task = CtxTool.fetch_task(ctx, state.url, or_create=True)
    #     task.vars = state.vars
    #     return task
    #
    # @classmethod
    # def task_to_state_msg(cls, task: Task, action: str) -> StateMsg:
    #     return StateMsg(
    #         url=cls.task_to_url(task),
    #         vars=task.vars,
    #         action=action,
    #     )
