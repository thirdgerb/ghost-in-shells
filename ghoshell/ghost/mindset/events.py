from abc import ABCMeta
from typing import Dict, Any

from ghoshell.ghost.intention import Intention
from ghoshell.ghost.url import URL


class Event(metaclass=ABCMeta):
    """
    调度事件机制
    发生在 Runtime 的调度过程中.
    """

    def __init__(self, target: URL, fr: URL | None):
        self.target = target
        self.fr = fr

    def destroy(self):
        del self.target
        del self.fr


# 事件体系是 Runtime 和 Think 之间的纽带.
# Runtime 的运行轨迹基于 Operator, 主要解决 Task 与 Task 之间的调度.
# 而 Event 则解决调度过程与每个 Think 之间的互动.
# 响应 Event 的是 mindset Stage


class Receiving(Event):
    """
    响应 Ghost 的 Input 产生的事件.
    会包含 Params, 是对 Input 解析后, 适配为结构化的参数
    """

    def __init__(self, current: URL, fr: URL | None, matched: Intention | None):
        self.matched = matched
        super().__init__(current, fr)

    def destroy(self):
        super().destroy()
        del self.matched


class Activating(Event):
    """
    重定向事件.
    """


class Callback(Event):
    """
    任务与任务之间的回调.
    """

    def __init__(self, finished: URL, depending: URL, result: Dict | None):
        super().__init__(depending, finished)
        self.result = result

    def destroy(self):
        del self.result
        super().destroy()


class Preempting(Event):
    """
    从中断的状态中恢复.
    """
    pass


class Withdrawing(Event):
    """
    从别的节点退回到当前节点.
    这个事件也可以被中断, 否则会链式地退出.
    """

    def __init__(self, current: URL, fr: URL | None, reason: Any | None):
        self.reason = reason
        super().__init__(current, fr)

    def destroy(self):
        del self.reason
        super().destroy()


# --- withdraw events --- #

class Canceling(Withdrawing):
    """
    任务取消
    """
    pass


class Quiting(Withdrawing):
    """
    对话退出
    """
    pass


class Failing(Withdrawing):
    """
    任务失败.
    """
    pass
