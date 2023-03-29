from abc import ABCMeta
from typing import Optional, Dict, Any

from ghoshell.ghost.mindset import Event, Thought
from ghoshell.ghost.uml import UML


class Activate(Event, metaclass=ABCMeta):
    """
    从一个节点主动进入到当前节点.
    """

    def __init__(self, this: Thought, fr: Optional[UML] = None):
        self.this = this
        self.fr: UML = fr

    def destroy(self):
        del self.this
        del self.fr


class Intercept(Event, metaclass=ABCMeta):
    """
    当前对话状态被打断, 跳转到另一个任务.
    先不实现
    """

    def __init__(self, this: Thought, args: Optional[Dict] = None):
        self.this = this
        self.args = args

    def destroy(self):
        del self.this
        del self.args


class Receive(Event, metaclass=ABCMeta):
    """
    响应 Ghost 的 Input 信息.
    """

    def __init__(self, this: Thought):
        self.this = this

    def destroy(self):
        del self.this


class Withdraw(Event, metaclass=ABCMeta):
    """
    从别的节点退回到当前节点.
    """

    def __init__(self, this: Thought, fr: Thought, reason: Optional[Any] = None):
        self.this = this
        self.fr: Thought = fr
        self.reason = reason

    def destroy(self):
        del self.this
        del self.fr
        del self.reason


# --- activate events --- #

class OnStart(Activate):
    pass


class OnRepeat(Activate):
    pass


class OnRedirect(Activate):
    pass


class OnDepend(Activate):
    pass


# --- interceptor --- #

class OnAttend(Activate):
    """
    命中了一个上下文中关注的意图.
    """
    pass


class OnPreempt(Activate):
    """
    blocking 状态的任务, 重新获得主动权.
    """
    pass


class OnIntend(Activate):
    """
    命中了一个全局意图.
    """
    pass


class OnAsync(Activate):
    """
    接受到异步回调消息, 以及数据.
    """
    pass


# --- receive events --- #


class OnFallback(Receive):
    """
    输入消息无法处理.
    """
    pass


# --- withdraw events --- #

class OnFinish(Withdraw):
    """
    被依赖的任务完成了, 回调当前任务.
    可以拿到
    """
    pass


class OnCancel(Withdraw):
    pass


class OnQuit(Withdraw):
    pass


class OnFailed(Withdraw):
    pass
