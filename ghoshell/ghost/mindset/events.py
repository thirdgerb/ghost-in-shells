from abc import ABCMeta
from typing import Dict

from ghoshell.url import URL


# 事件体系是 Runtime 和 Think 之间的纽带.
# Runtime 的运行轨迹基于 Operator, 主要解决 Task 与 Task 之间的调度.
# 而 Event 则解决调度过程与每个 Think 之间的互动.
# 响应 Event 的是 intentions Stage


class Event(metaclass=ABCMeta):
    """
    调度事件机制
    发生在 Runtime 的调度过程中.
    """

    def __init__(self, task_id: str, stage: str, fr: URL | None):
        self.task_id = task_id  # task_id
        self.stage = stage
        self.fr = fr  # task_id

    def destroy(self):
        del self.task_id
        del self.stage
        del self.fr


class OnReceived(Event):
    pass


class OnActivating(Event):
    """
    重定向事件.
    """


class OnCallback(Event):
    """
    任务与任务之间的回调.
    """

    def __init__(self, task_id: str, stage: str, fr: URL, data: Dict | None):
        super().__init__(task_id, stage, fr)
        self.data = data

    def destroy(self):
        del self.data
        super().destroy()


class OnPreempted(Event):
    """
    从中断的状态中恢复.
    """
    pass


class OnWithdrawing(Event, metaclass=ABCMeta):
    """
    从别的节点退回到当前节点.
    这个事件也可以被中断, 否则会链式地退出.
    """


# --- withdraw events --- #

class OnCanceling(OnWithdrawing):
    """
    任务取消
    """
    pass


class OnQuiting(OnWithdrawing):
    """
    对话退出
    """
    pass


class OnFailing(OnWithdrawing):
    """
    任务失败.
    """
    pass
