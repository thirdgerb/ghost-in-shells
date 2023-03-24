from ghoshell.ghost import Event, UML, Task


class OnStart(Event):
    """
    启动一个 Stage, 通常来自另一个节点.
    """

    def __init__(self, fr: UML, to: UML):
        self.fr = fr
        self.to = to

    @property
    def current(self) -> UML:
        return self.to


class OnFallback(Event):
    """
    消息未被拦截处理, 触发回调.
    """

    def __init__(self, uml: UML):
        self.uml = uml

    @property
    def current(self) -> UML:
        return self.uml


class OnDepend(Event):
    """
    一个任务依赖另一个任务.
    接到这个依赖通知的是另一个任务.
    """

    def __init__(self, fr: Task, to: UML):
        self.fr = fr
        self.to = to

    @property
    def current(self) -> UML:
        return self.to


class OnCallback(Event):
    """
    一个任务已经完成,触发了回调
    """

    def __init__(self, fr: Task, to: UML):
        self.fr = fr
        self.to = to

    @property
    def current(self) -> UML:
        return self.to