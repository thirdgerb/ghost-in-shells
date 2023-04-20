from abc import ABCMeta
from typing import Optional, Dict, Any

from ghoshell.ghost.mindset import Event, Thought
from ghoshell.ghost.uml import UML


# 事件体系是 Runtime 和 Think 之间的纽带.
# Runtime 的运行轨迹基于 Operator, 主要解决 Task 与 Task 之间的调度.
# 而 Event 则解决调度过程与每个 Think 之间的互动.
# 响应 Event 的是 mindset Stage


class OnActivate(Event, metaclass=ABCMeta):
    """
    从一个节点主动进入到当前节点.
    """

    def __init__(self, this: Thought, fr: Optional[UML] = None):
        self.this = this
        self.fr: UML = fr

    def destroy(self):
        del self.this
        del self.fr


class OnIntercept(Event, metaclass=ABCMeta):
    """
    当前对话状态被打断, 跳转到另一个任务.
    先不实现
    """

    def __init__(self, this: Thought, fr: Optional[UML] = None):
        self.this = this
        self.fr = fr

    def destroy(self):
        del self.this
        del self.fr


class OnReceive(Event, metaclass=ABCMeta):
    """
    响应 Ghost 的 Input 信息.
    """

    def __init__(self, this: Thought, params: Optional[Dict], fr: UML | None = None):
        self.this = this
        self.params = params
        self.fr = fr

    def destroy(self):
        del self.this
        del self.params
        del self.fr


class OnCallback(Event):
    """
    系统任务之间的回调.
    """

    def __init__(self, this: Thought, result: Dict):
        self.this = this
        self.result = result

    def destroy(self):
        del self.this
        del self.result


class OnWithdraw(Event, metaclass=ABCMeta):
    """
    从别的节点退回到当前节点.
    """

    def __init__(self, this: Thought, fr: Optional[UML] = None, reason: Optional[Any] = None):
        self.this: Thought = this
        self.fr: UML = fr
        self.reason: Any = reason

    def destroy(self):
        del self.this
        del self.fr
        del self.reason


# --- activate events --- #

class OnStart(OnActivate):
    """
    正常启动一个事件.
    """
    pass


class OnRepeat(OnActivate):
    """
    重复当前对话
    """
    pass


class OnPreempt(OnActivate):
    """
    blocking 状态的任务, 重新获得主动权.
    """
    pass


# --- interceptor --- #

class OnDepended(OnIntercept):
    pass


class OnRedirect(OnIntercept):
    pass


# --- receive events --- #

class OnAttend(OnReceive):
    """
    命中了一个上下文中关注的意图.
    """
    pass


class OnIntend(OnReceive):
    """
    命中了一个全局意图.
    """
    pass


class OnFallback(OnReceive):
    """
    输入消息无法处理.
    """
    pass


# --- withdraw events --- #

class OnCancel(OnWithdraw):
    """
    任务取消
    """
    pass


class OnQuit(OnWithdraw):
    """
    对话退出
    """
    pass


class OnFailed(OnWithdraw):
    """
    任务失败.
    """
    pass
