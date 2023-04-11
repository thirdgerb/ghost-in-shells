from __future__ import annotations

from typing import Optional, Dict

from ghoshell.ghost.attention import Intention
from ghoshell.ghost.context import Context
from ghoshell.ghost.exceptions import MindsetNotFoundException, RuntimeException
from ghoshell.ghost.io import StateMsg
from ghoshell.ghost.mindset import Thought, Stage, Event
from ghoshell.ghost.runtime import Task
from ghoshell.ghost.uml import UML


class CtxTool:

    @classmethod
    def match_intention(cls, ctx: "Context", think: str, stage: str) -> Optional[Intention]:
        stage = cls.fetch_stage(ctx, think, stage)
        metas = stage.intentions(ctx)
        return ctx.clone.attentions.match(ctx, *metas)

    @classmethod
    def instance_thought(cls, ctx: "Context", thought: Thought) -> "Thought":
        mind = ctx.clone.mind
        think = mind.force_fetch(thought.think)
        task = ctx.clone.runtime.fetch_task(thought.tid, think.is_long_term())

        stage = think.fetch_stage(task.stage)
        if stage is None:
            raise MindsetNotFoundException("todo")
        return cls.merge_thought_from_task(thought, task)

    @classmethod
    def complete_task(cls, ctx: "Context", task: Task) -> Task:
        mind = ctx.clone.mind
        think = mind.force_fetch(task.resolver)
        stage = think.fetch_stage(task.stage)
        if stage is None:
            raise MindsetNotFoundException("todo")
        task.overdue = think.overdue
        task.level = stage.level
        return task

    @classmethod
    def thought_to_uml(cls, thought: Thought) -> UML:
        return UML(think=thought.think, stage=thought.stage, args=thought.args.copy())

    @classmethod
    def task_to_uml(cls, task: Task) -> UML:
        return UML(think=task.resolver, stage=task.stage, args=task.args.copy())

    @classmethod
    def merge_thought_from_task(cls, thought: Thought, task: Task) -> "Thought":
        """
        从 task 中重置当前状态.
        """
        thought.set_variables(task.vars)
        thought.stage = task.stage
        return thought

    @classmethod
    def join_thought_to_task(cls, thought: Thought, task: Task) -> Task:
        task.vars = thought.vars()
        return task

    @classmethod
    def task_result(cls, ctx: Context, task: Task) -> Optional[Dict]:
        thought = cls.fetch_thought_by_task(ctx, task)
        return cls.thought_result(ctx, thought)

    @classmethod
    def thought_result(cls, ctx: Context, thought: Thought) -> Optional[Dict]:
        think = ctx.clone.mind.force_fetch(thought.think)
        return think.result(thought)

    @classmethod
    def new_task_by_thought(cls, ctx: Context, thought: Thought) -> Task:
        uml = cls.thought_to_uml(thought)
        return cls.new_task_from_uml(ctx, uml)

    @classmethod
    def new_tid(cls, ctx: Context, uml: UML) -> str:
        think = ctx.clone.mind.force_fetch(uml.think)
        return think.new_task_id(ctx, uml.args)

    @classmethod
    def fetch_task_by_tid(cls, ctx: Context, tid: str) -> Optional[Task]:
        runtime = ctx.clone.runtime
        process = runtime.current_process()
        return process.get_task(tid)

    @classmethod
    def fire_event(cls, ctx: Context, event: Event):
        stage = cls.fetch_stage(ctx, event.this.think, event.this.stage)
        return stage.on_event(ctx, event)

    @classmethod
    def save_thought(cls, ctx: Context, thought: Thought) -> None:
        task = cls.fetch_task_by_thought(ctx, thought)
        ctx.clone.runtime.store_task(task)

    @classmethod
    def save_task(cls, ctx: Context, task: Task) -> None:
        ctx.clone.runtime.store_task(task)

    @classmethod
    def fetch_task(cls, ctx: Context, uml: UML, or_create: bool = True) -> Optional[Task]:
        clone = ctx.clone
        mindset = clone.mind
        think = mindset.fetch(uml.think)
        if think is None:
            return None
        tid = think.new_task_id(ctx, uml.args)
        runtime = clone.runtime
        process = runtime.current_process()
        task = process.get_task(tid)
        if task is not None:
            return task

        if think.is_long_term():
            task = runtime.fetch_long_term_task(tid)
        if task is not None:
            return task

        if not or_create:
            return None

        return Task(
            tid=tid,
            resolver=uml.think,
            stage="",
            args=uml.args.copy(),
        )

    @classmethod
    def fetch_thought_by_task(cls, ctx: Context, task: Task) -> Thought:
        think = ctx.clone.mind.force_fetch(task.resolver)
        thought = think.new_thought(ctx, task.args)
        if thought.tid != task.tid:
            raise RuntimeException("todo")
        return cls.merge_thought_from_task(thought, task)

    @classmethod
    def fetch_task_by_thought(cls, ctx: Context, thought: Thought, or_create: bool = True) -> Optional[Task]:
        clone = ctx.clone
        think = clone.mind.fetch(thought.think)
        task = clone.runtime.fetch_task(thought.tid, think.is_long_term())
        if task is None:
            if not or_create:
                return None
            return cls.new_task_by_thought(ctx, thought)

        task = cls.join_thought_to_task(thought, task)
        return cls.complete_task(ctx, task)

    @classmethod
    def fetch_thought(cls, ctx: Context, uml: UML) -> "Thought":
        """
        语法糖
        """
        think = ctx.clone.mind.force_fetch(uml.think)
        thought = think.new_thought(ctx, uml.args)
        return cls.instance_thought(ctx, thought)

    @staticmethod
    def fetch_stage(ctx: Context, think: str, stage: str) -> "Stage":
        """
        语法糖
        """
        think = ctx.clone.mind.fetch(think)
        stage = think.fetch_stage(stage)
        if stage is None:
            raise MindsetNotFoundException("todo")
        return stage

    @classmethod
    def state_msg_to_task(cls, ctx: Context, state: StateMsg) -> Task:
        task = CtxTool.fetch_task(ctx, state.uml, or_create=True)
        task.vars = state.vars
        return task

    @classmethod
    def task_to_state_msg(cls, task: Task, action: str) -> StateMsg:
        return StateMsg(
            uml=cls.task_to_uml(task),
            vars=task.vars,
            action=action,
        )

    @classmethod
    def new_task_from_uml(cls, ctx: Context, uml: UML) -> Task:
        think = ctx.clone.mind.force_fetch(uml.think)
        # 根据任务初始化
        task = Task(
            tid=think.new_task_id(ctx, uml.args),
            resolver=uml.think,
            stage="",
            is_long_term=think.is_long_term(),
            args=uml.args.copy(),
        )
        thought = think.new_thought(ctx, uml.args)
        task = cls.join_thought_to_task(thought, task)
        return cls.complete_task(task)
