from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Dict

from ghoshell.ghost.runtime import TaskLevel, TaskStatus
from ghoshell.url import URL


class Thought(metaclass=ABCMeta):
    """
    当前任务的状态.
    可以理解成一个函数的运行栈
    args 是入参
    vars 则是运行中的变量.

    这个 This 需要每个 Think 能力自定义一个协议, 主要是 variables 需要一个协议.

    thought 的生命周期: task => thought => task
    thought 是 task 与 intentions 互动时的中间态数据, 用来做强类型提示.
    """
    tid: str = ""
    url: URL | None = None

    # 当前任务的过期时间. 如果
    # overdue == 0, 表示跟随进程走, 随时可回收.
    # overdue < 0, 表示任务是不过期的长程记忆.
    # overdue > 0, 表示任务在 overdue 秒后过期.
    overdue: int = 0

    # 当前任务的优先级, 影响到排序, 修改影响 task
    # priority < 0  任务中断时, 会遗忘.
    # priority == 0 任务中断时, 会等待回调.
    # priority > 0 任务在 Preempting 状态时, 会根据优先级排序.
    priority: float = 0

    # 当前任务的开放度, 修改影响 task
    level: int = TaskLevel.LEVEL_PUBLIC

    # 当前任务的状态. 传入值, 修改没有意义.
    status: int = TaskStatus.NEW

    def __init__(
            self,
            args: Dict
    ):
        self.prepare(args)

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
    def vars(self) -> Dict | None:
        """
        返回当前上下文中的变量.
        """
        pass

    def dict(self):
        return dict(
            url=self.url.model_dump() if self.url else None,
            tid=self.tid,
            level=self.level,
            status=self.status,
            priority=self.priority,
            overdue=self.overdue,
            vars=self.vars(),
        )

    def destroy(self) -> None:
        del self.url
        del self.tid
        del self.level
        del self.status
        del self.priority


class DictThought(Thought):
    data: Dict = {}

    def prepare(self, args: Dict) -> None:
        return

    def set_variables(self, variables: Dict) -> None:
        self.data = variables

    def vars(self) -> Dict | None:
        return self.data

    def _destroy(self) -> None:
        del self.data
