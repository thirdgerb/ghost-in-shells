from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, Dict, Callable

from pydantic import BaseModel

from ghoshell.ghost.context import Context
from ghoshell.ghost.intention import Intention
from ghoshell.ghost.operate import Operator
from ghoshell.ghost.runtime import Task, TASK_STATUS, TASK_LEVEL, TaskStatus, TaskLevel
from ghoshell.ghost.uml import UML


class Thought(metaclass=ABCMeta):
    """
    当前任务的状态.
    可以理解成一个函数的运行栈
    args 是入参
    vars 则是运行中的变量.
    result 对应了 return 的值.

    这个 This 需要每个 Think 能力自定义一个协议.
    """

    # 任务的唯一 ID
    tid: str

    uml: UML

    # 任务的状态. 对齐 runtime 的状态.
    status: TASK_STATUS

    # 当前任务所在的 stage 状态位.
    stage: str = ""

    level: TASK_LEVEL = TaskLevel.LEVEL_PUBLIC

    def __init__(self, task_id: str, uml: UML):
        self.tid = task_id
        self.status = TaskStatus.TASK_NEW
        self.uml = uml
        self.stage = ""
        self.prepare(self.uml.args)

    def from_task(self, task: Task) -> Thought:
        """
        从 task 中重置当前状态.
        """
        self.status = task.status
        self.uml = task.uml
        self.set_variables(task.data)
        return self

    def to_task(self, task: Task) -> Task:
        """
        根据当前状态, 重置 task 状态.
        """
        task.priority = self.priority()
        task.data = self.vars()
        task.overdue = self.overdue()
        task.level = self.level
        # 设定 task 的返回值. 前提是 task 的返回值一直是 None
        if task.status == TaskStatus.TASK_FINISHED and task.result is None:
            task.result = self.returning()
        return task

    def priority(self) -> float:
        """
        当前任务的状态.
        """
        return 0

    def overdue(self) -> int:
        """
        任务过期时间. 过期后的任务会被 GC
        为 -1 表示没有过期.
        """
        return -1

    # ---- 抽象方法 ---- #
    @abstractmethod
    def prepare(self, args: Dict) -> None:
        """
        初始化
        """
        pass

    @abstractmethod
    def set_variables(self, variables: Dict) -> None:
        """
        设置上下文数据, 通常是一个 dict, 可以用 BaseModel 转成协议.
        """
        pass

    @abstractmethod
    def vars(self) -> Dict:
        """
        返回当前上下文中的变量.
        """
        pass

    @abstractmethod
    def returning(self) -> Optional[Dict]:
        """
        从当前状态中返回一个结果.
        """
        pass


class Event(metaclass=ABCMeta):
    """
    事件机制
    """

    this: Thought
    kind: str

    @abstractmethod
    def destroy(self):
        """
        为了方便 python 的 gc
        主动删除掉一些持有元素
        避免循环依赖.
        """
        pass


class ThinkMeta(BaseModel):
    uml: UML
    driver: str
    config: Dict


class Think(BaseModel, metaclass=ABCMeta):
    """
    ghost 拥有的思维模块
    """

    @abstractmethod
    def to_meta(self) -> ThinkMeta:
        pass

    @classmethod
    @abstractmethod
    def from_meta(cls, meta: ThinkMeta) -> "Think":
        pass

    @property
    @abstractmethod
    def uml(self) -> UML:
        """
        用类似 url (uniform resource locator) 的方式定位一个 Thinking
        """
        pass

    @abstractmethod
    def new_thought(self, ctx: Context, args: Dict) -> Thought:
        """
        结合上下文, 初始化一个 Thinking 的状态.
        这个状态用 This 来表示, 可以和 runtime 的 Task 互通.
        显然这个状态要解决 task_id 的问题. 可以根据上下文设计自己的 task id 机制.
        比如, 根据发出事件的 subject_id 来对应一个全局唯一的 task.
        """
        pass

    def default_stage(self) -> Stage:
        """
        返回默认的 state
        """
        pass

    def all_stages(self) -> Dict[str, Stage]:
        """
        返回所有可能的状态.
        可能只有一个状态.
        """
        pass


THINK_DRIVER = Callable[[ThinkMeta], Think]


class Stage(metaclass=ABCMeta):
    """
    Thinking 的状态位.
    基本的状态位类型:
    - 内部计算节点
    -
    """

    @property
    @abstractmethod
    def uml(self) -> UML:
        pass

    @abstractmethod
    def level(self, this: Thought) -> int:
        pass

    @abstractmethod
    def intention(self, ctx: Context) -> Optional[Intention]:
        pass

    @abstractmethod
    def on_event(self, ctx: Context, e: "Event") -> Optional[Operator]:
        """
        当一个算子执行到当前位置时, 可以定义事件的响应逻辑.
        做必要的动作, 或者终止当前算子的执行, 开启一个新流程.
        常见的事件算子: 依赖回调, 取消, 退出, 异常等.
        """
        pass


class Mindset(metaclass=ABCMeta):
    """
    定义了 Ghost 拥有的思维方式
    核心是可以通过 UniformReactionLocator 取出 Reaction
    """

    @abstractmethod
    def fetch(self, thinking: str) -> Optional[Think]:
        """
        获取一个 Thinking
        """
        pass

    @abstractmethod
    def register_driver(self, key: str, driver: THINK_DRIVER) -> None:
        """
        注册 think 的驱动.
        """
        pass

    @abstractmethod
    def register_meta(self, meta: ThinkMeta) -> None:
        """
        注册一个 thinking
        当然, Mindset 可以有自己的实现, 从某个配置体系中获取.
        或者合并多个 Mindset.
        """
        pass

    def register_think(self, think: Think) -> None:
        """
        用现成的 Think 完成注册.
        """
        meta = think.to_meta()
        self.register_meta(meta)
        self.register_driver(meta.driver, think.from_meta)
