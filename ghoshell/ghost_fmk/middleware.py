from abc import ABCMeta, abstractmethod
from typing import Callable

from ghoshell.ghost import Context, Ghost

GHOST_PIPELINE = Callable[[Context], Context]
GHOST_PIPE = Callable[[Context, GHOST_PIPELINE], Context]


class IMiddleware(metaclass=ABCMeta):
    """
    组件
    """

    @abstractmethod
    def new(self, ghost: Ghost) -> GHOST_PIPE:
        pass


def mock_pipe(_input: Context, after: GHOST_PIPELINE) -> Context:
    return after(_input)


class ExceptionHandlerMiddleware(IMiddleware):
    """
    全局处理异常的中间件.
    需要将会话异常处理成正常的回复, 并且计数
    超过预期次数后, 需要重置所有的对话.
    """

    def new(self, ctx: Context) -> GHOST_PIPE:
        # todo: 需要实现
        return mock_pipe
