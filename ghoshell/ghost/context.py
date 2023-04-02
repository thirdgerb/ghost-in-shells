from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Any, Optional, TYPE_CHECKING

from ghoshell.ghost.exceptions import MindsetNotFoundException, RuntimeException
from ghoshell.ghost.features import IFeaturing
from ghoshell.ghost.intention import Attentions
from ghoshell.ghost.io import Input, Output, Message
from ghoshell.ghost.mindset import Mindset
from ghoshell.ghost.runtime import Runtime, Task, TaskPtr, TaskData
from ghoshell.ghost.session import Session
from ghoshell.ghost.uml import UML

if TYPE_CHECKING:
    from ghoshell.ghost.mindset import Thought, Stage
    from ghoshell.ghost.operate import Operate, OperatorManager


class Context(metaclass=ABCMeta):
    """
    Ghost 运行时的上下文, 努力包含一切核心逻辑与模块
    """

    @property
    @abstractmethod
    def ghost_name(self) -> str:
        """
        机器人的"灵魂"，不同的 Ghost 可能使用同样的灵魂，比如"微软小冰"等
        """
        pass

    @property
    @abstractmethod
    def session(self) -> Session:
        """
        机器人灵魂的"实例",用来隔离 process 与记忆
        """
        pass

    @abstractmethod
    def root(self) -> UML:
        pass

    @property
    @abstractmethod
    def input(self) -> Input:
        """
        请求的输入消息, 任何时候都不应该变更.
        """
        pass

    @abstractmethod
    def output(self, *actions: Message) -> None:
        """
        输出各种动作, 实际上输出到 output 里, 给 shell 去处理
        """
        pass

    @abstractmethod
    def async_input(self, _input: Input) -> None:
        """
        ghost 给 ghost 发送信息时使用
        """
        pass

    @abstractmethod
    def reset_input(self, _input: Input) -> None:
        """
        重置上下文的 Input
        """
        pass

    @abstractmethod
    def operate(self, this: "Thought") -> "Operate":
        """
        返回上下文的操作工具
        """
        pass

    @property
    @abstractmethod
    def mind(self) -> Mindset:
        """
        用来获取所有的记忆.
        """
        pass

    @property
    @abstractmethod
    def runtime(self) -> Runtime:
        """
        与 上下文/进程 相关的存储单元, 用来存储各种数据
        """
        pass

    @property
    @abstractmethod
    def featuring(self) -> IFeaturing:
        """
        从上下文中获取特征.
        特征是和上下文相关的任何信息.
        通常不包含记忆.
        """
        pass

    @property
    @abstractmethod
    def attentions(self) -> Attentions:
        """
        机器人状态机当前保留的工程化注意力机制
        与算法不同, 注意的可能是命令行, API, 事件等复杂信息.
        """
        pass

    @abstractmethod
    def gen_output(self) -> Output:
        """
        将所有的输出动作组合起来, 输出为 Output
        所有 act 会积累新的 action 到 output
        它应该是幂等的, 可以多次输出.
        """
        pass

    @abstractmethod
    def reset_output(self, output: Output) -> None:
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        上下文级别的缓存机制, 用在内存中.
        """
        pass

    def get(self, key: str) -> Optional[Any]:
        """
        从上下文中获取缓存. 工具机制.
        可惜没有泛型, python 很麻烦的.
        """
        pass

    @abstractmethod
    def new_operator_manager(self) -> "OperatorManager":
        """
        返回一个 OperatorManager
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        上下文运行完成后, 需要考虑 python 的特点, 要主动清理记忆
        """
        pass


class CtxTool:

    @staticmethod
    def fetch_thought_by_task(ctx: Context, task: Task) -> Thought:
        think = ctx.mind.fetch(task.ptr.resolver)
        thought = think.new_thought(ctx, task.data.args)
        if thought.tid != task.ptr.tid:
            # todo
            raise RuntimeException("不兼容的问题")
        return thought.merge_from_task(task)

    @staticmethod
    def fetch_task_by_thought(ctx: Context, thought: Thought) -> Task:
        task = ctx.runtime.fetch_task(thought.tid)
        if task is None:
            task = Task(
                ptr=TaskPtr(
                    tid=thought.tid,
                    resolver=thought.uml.think,
                    stage=thought.uml.stage,
                ),
                data=TaskData(
                    args=thought.uml.args.copy(),
                )
            )
            task = thought.join_to_task(task)
        return task

    @staticmethod
    def new_thought(ctx: Context, uml: UML) -> "Thought":
        think = ctx.mind.fetch(uml.think)
        stage = think.all_stages().get(uml.stage, None)
        if stage is None:
            # todo
            raise MindsetNotFoundException("")
        thought = think.new_thought(ctx, uml.args)
        thought.level = stage.level(thought)
        return thought

    @classmethod
    def fetch_thought(cls, ctx: Context, uml: UML) -> "Thought":
        """
        语法糖
        """
        thought = cls.new_thought(ctx, uml)
        # 获取一个 task 实例
        task = CtxTool.fetch_task_by_thought(ctx, thought)
        thought.merge_from_task(task)
        # 根据 stage 的实现来提供 level
        return thought

    @staticmethod
    def fetch_stage(ctx, uml: UML) -> "Stage":
        """
        语法糖
        """
        think = ctx.mind.fetch(uml.think)
        return think.all_stages().get(uml.stage)
