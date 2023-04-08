from abc import ABCMeta, abstractmethod
from typing import Callable, Optional

from ghoshell.ghost import Context, Input, Output

GHOST_PIPELINE = Callable[[Input], Optional[Output]]
GHOST_PIPE = Callable[[Input, GHOST_PIPELINE], Optional[Output]]


class IMiddleware(metaclass=ABCMeta):
    """
    组件
    """

    @abstractmethod
    def new(self, ctx: Context) -> GHOST_PIPE:
        pass


def mock_pipe(_input: Input, after: GHOST_PIPELINE) -> Optional[Output]:
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
