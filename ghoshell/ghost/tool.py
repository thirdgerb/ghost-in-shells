from __future__ import annotations

from logging import Logger
from typing import Optional, Dict, List, Tuple

from pydantic import ValidationError

from ghoshell.ghost.context import Context
from ghoshell.ghost.exceptions import MindsetNotFoundException, RuntimeException
from ghoshell.ghost.mindset import Intention, Attention
from ghoshell.ghost.mindset import Think, Thought, Stage, Event
from ghoshell.ghost.mindset.operator import Operator
from ghoshell.ghost.runtime import Task, TaskStatus, Process, TaskLevel
from ghoshell.url import URL

GroupedIntentions = Dict[str, List[Intention]]


class CtxTool:
    """
    基于抽象实现的一些基础上下文工具.
    上下文是面向开发者的用户态操作, 操作的主体是 Stage, 操作的对象是 Event, url 和 Thought
    而 task 是 runtime 操作的对象, 两者应该严格隔离开, 否则调度流程会极不清晰
    因此有 CtxTool 和 RuntimeTool 两种.
    """

    @classmethod
    def logger(cls, ctx: "Context") -> Logger:
        return ctx.container.force_fetch(Logger)

    @classmethod
    def fetch_thought(cls, ctx: "Context", url: URL) -> Thought:
        task = RuntimeTool.fetch_task_by_url(ctx, url, True)
        return RuntimeTool.fetch_thought_by_task(ctx, task)

    @classmethod
    def fetch_current_thought(cls, ctx: "Context") -> Thought:
        task = RuntimeTool.fetch_current_task(ctx)
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
        think = ctx.clone.mindset.force_fetch(task.url.think)
        return True, think.result(ctx, thought)

    # ---- thought 相关方法 ----#

    @classmethod
    def force_fetch_stage(cls, ctx: Context, think: str, stage: str) -> "Stage":
        """
        取出一个 think.stage, 不存在要抛出异常.
        """
        stage_instance = cls.fetch_stage(ctx, think, stage)
        if stage_instance is None:
            raise MindsetNotFoundException(f"force fetch think '{think}' with stage '{stage}' failed, not found")
        return stage_instance

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
                intention.target = attention.to
                intention.reaction = attention.reaction

            grouped_intentions = cls.group_intentions(grouped_intentions, attention.intentions)
        ordered_kinds = ctx.clone.focus.kinds()
        focus = ctx.clone.focus
        for kind in ordered_kinds:
            if kind not in grouped_intentions:
                continue
            intentions = grouped_intentions[kind]
            matched = focus.match(ctx, kind, *intentions)
            if matched is not None:
                return matched
        return None

    @classmethod
    def context_intentions(
            cls,
            ctx: "Context",
    ) -> GroupedIntentions:
        """
        从上下文的 attentions 中解析出 intentions
        """
        attentions = cls.context_attentions(ctx)
        grouped_intentions: GroupedIntentions = {}
        for attention in attentions:
            for intention in attention.intentions:
                # 标记索引.
                intention.target = attention.to
                intention.reaction = attention.reaction

            grouped_intentions = cls.group_intentions(grouped_intentions, attention.intentions)
        return grouped_intentions

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
        return ctx.clone.focus.global_match(ctx)

    @classmethod
    def current_think_stage(cls, ctx: "Context") -> Stage:
        task = RuntimeTool.fetch_current_task(ctx)
        return cls.fetch_stage(ctx, task.url.think, task.url.stage)

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
        awaiting_task = RuntimeTool.fetch_current_task(ctx)
        # public, protected, private
        awaiting_task_level = awaiting_task.level

        # awaiting 永远最高优.
        if awaiting_task.attentions:
            # awaiting 添加所有.
            for attention in awaiting_task.attentions:
                result.append(attention)

        if root_task.tid != awaiting_task.tid and root_task.attentions is not None:
            for attention in root_task.attentions:
                # root 非私有方法都可以添加进去, 而且是高优.
                if attention.level != TaskLevel.LEVEL_PRIVATE:
                    result.append(attention)

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

    # @classmethod
    # def _add_task_intentions(
    #         cls,
    #         ctx: Context,
    #         result: GroupedIntentions,
    #         task: Task,
    #         private: bool,
    #         forward: bool,
    # ) -> GroupedIntentions:
    #
    #     fr = None
    #     if forward:
    #         fr = task.url
    #         url_list = task.intentions
    #     else:
    #         url_list = [task.url]
    #
    #     if not url_list:
    #         return result
    #
    #     for target in url_list:
    #         stage = CtxTool.force_fetch_stage(ctx, target.think, target.stage)
    #
    #         # 从 stage 里获取 intention
    #         intentions = stage.intentions(ctx)
    #         if not intentions:
    #             continue
    #         #  初始化 intentions
    #         for intention in intentions:
    #             # 添加好关联路径.
    #             intention.target = fr
    #
    #         # 从 intentions 组装成为 GroupedIntentions
    #         for meta in intentions:
    #             # 私有意图无法在非私有场景使用.
    #             if meta.private and not private:
    #                 continue
    #             kind = meta.kind
    #             if kind not in result:
    #                 result[kind] = []
    #             result[kind].append(meta)
    #     return result


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
            awaiting = RuntimeTool.fetch_current_task(ctx)
            event.fr = awaiting.url.copy_with()

        # 用 task 的信息补完 thought
        task = cls.force_fetch_task(ctx, event.task_id)

        # 初始化 thought. 这个 thought 里应该包含正确的 tid.
        # 将变量注入到 thought.
        thought = cls.fetch_thought_by_task(ctx, task)
        thought.url.stage = event.stage

        # 触发事件. 要使用 event 的 stage
        stage = CtxTool.force_fetch_stage(ctx, thought.url.think, thought.url.stage)
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
        task = ctx.runtime.instance_task(task)
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
            raise RuntimeException(f"force fetch task with id {tid} failed")
        return task

    @classmethod
    def fetch_root_task(cls, ctx: Context) -> Task:
        runtime = ctx.runtime
        process = runtime.current_process()
        task = runtime.fetch_task(process.root)
        if task is None:
            raise RuntimeException("fetch root task failed")
        return task

    @classmethod
    def fetch_current_task(cls, ctx: Context) -> Task:
        runtime = ctx.runtime
        process = runtime.current_process()
        task = runtime.fetch_task(process.current)
        if task is None:
            raise RuntimeException("fetch awaiting task failed")
        return task

    @classmethod
    def new_thought(cls, ctx: Context, url: URL) -> "Thought":
        """
        根据 url 初始化一个 thought
        并没有执行实例化
        """
        think = ctx.clone.mindset.force_fetch(url.think)
        args_type = think.args_type()
        if args_type is not None:
            try:
                args_type(**url.args)
            except ValidationError as e:
                raise RuntimeException(str(e))
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
        if task.status != TaskStatus.NEW:
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
        think = ctx.clone.mindset.force_fetch(url.think)
        return think.result(ctx, thought)

    @classmethod
    def new_task(cls, ctx: Context, url: URL) -> Task:
        """
        根据 url 初始化一个 task
        """
        tid = cls.new_task_id(ctx, url)
        task = Task(
            tid=tid,
            url=url.model_dump(),
        )
        thought = cls.new_thought(ctx, url)
        cls.merge_thought_to_task(thought, task)
        return task

    @classmethod
    def new_task_id(cls, ctx: Context, url: URL) -> str:
        # todo: 以后实现一个 ctx 级别的缓存, 避免重复生成.
        clone = ctx.clone
        mindset = clone.mindset
        think = mindset.force_fetch(url.think)
        tid = think.new_task_id(ctx, url.args)
        return tid

    @classmethod
    def store_task(cls, ctx: Context, *tasks: Task) -> None:
        if len(tasks) > 0:
            ctx.runtime.store_task(*tasks)

    @classmethod
    def store_process(cls, ctx: Context, process: Process) -> None:
        ctx.runtime.store_process(process)

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
    #     intentions = clone.mind
    #     think = intentions.fetch(url.think)
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
    #         think=url.think,
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
