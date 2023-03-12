from typing import Optional

from ghoshell.ghost import IOperator, IContext, This


class Depend(IOperator):
    """
    当前任务依赖另一个任务
    """
    pass


class Finish(IOperator):
    """
    当前任务结束
    """

    def __init__(self, this: This):
        self.this: This = this

    def run(self, ctx: IContext) -> Optional[IOperator]:
        pass


class Cancel(IOperator):
    pass


class Redirect(IOperator):
    pass


class Intend(IOperator):
    pass


class Quit(IOperator):
    pass


class Fail(IOperator):
    pass


class Fallback(IOperator):
    pass


class Wake(IOperator):
    pass


class Retain(IOperator):
    pass


class Callback(IOperator):
    pass
