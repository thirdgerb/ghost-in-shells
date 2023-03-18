from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, List, Dict

from ghoshell.ghost.context import IContext
from ghoshell.ghost.intention import Intention
from ghoshell.ghost.operator import IOperator
from ghoshell.ghost.runtime import Task, TASK_STATUS, TASK_NEW, TASK_FINISHED
from ghoshell.ghost.uml import UML


class This(metaclass=ABCMeta):
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

    def __init__(self, task_id: str, uml: UML):
        self.tid = task_id
        self.status = TASK_NEW
        self.uml = uml
        self.prepare(uml.args)
        self.stage = ""

    def from_task(self, task: Task) -> None:
        self.status = task.status
        self.stage = task.stage
        self.set_variables(task.data)

    def to_task(self, task: Task) -> Task:
        task.priority = self.priority()
        task.data = self.vars()
        task.overdue = self.overdue()
        if task.status == TASK_FINISHED:
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


class Thinking(metaclass=ABCMeta):
    """
    ghost 拥有的思维模块
    """

    @property
    @abstractmethod
    def uml(self) -> UML:
        """
        用类似 url (uniform resource locator) 的方式定位一个 Thinking
        """
        pass

    @abstractmethod
    def receiver(self, ctx: IContext, uml: UML) -> This:
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


class Stage(metaclass=ABCMeta):
    """
    Thinking 的状态位.
    """

    @abstractmethod
    def intention(self, this: This) -> Intention:
        """
        进入当前状态可以提供的各种意图.
        """
        pass

    @abstractmethod
    def is_staging(self) -> bool:
        """
        当前节点是有状态的, 还是无状态的.
        """
        pass

    @abstractmethod
    def attentions(self, this: This, ctx: IContext) -> List[UML]:
        """
        从当前状态进入别的状态的连接点
        attentions with intentions
        """
        pass

    @abstractmethod
    def on_event(self, this: This, ctx: IContext, op: IOperator) -> IOperator:
        """
        当一个事件执行到当前位置时, 可以在它执行之前进行拦截
        做必要的动作.
        常见的事件: 依赖回调, 取消, 退出, 异常等.
        """
        pass


class Mindset(metaclass=ABCMeta):
    """
    定义了 Ghost 拥有的思维方式
    核心是可以通过 UniformReactionLocator 取出 Reaction
    """

    @abstractmethod
    def fetch(self, thinking: str) -> Optional[Thinking]:
        """
        获取一个 Thinking
        """
        pass

    @abstractmethod
    def register(self, uml: UML, thinking: Thinking) -> None:
        """
        注册一个 thinking
        当然, Mindset 可以有自己的实现, 从某个配置体系中获取.
        或者合并多个 Mindset.
        """
        pass
