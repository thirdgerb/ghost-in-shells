from abc import ABCMeta, abstractmethod
from typing import Callable

from ghoshell.ghost import Context, Ghost

CtxPipeline = Callable[[Context], Context]
CtxPipe = Callable[[Context, CtxPipeline], Context]


class CtxMiddleware(metaclass=ABCMeta):
    """

    """

    @abstractmethod
    def new(self, ghost: Ghost) -> CtxPipe:
        pass


def mock_pipe(_input: Context, after: CtxPipeline) -> Context:
    return after(_input)


class ExceptionHandlerMiddleware(CtxMiddleware):
    """
    全局处理异常的中间件.
    需要将会话异常处理成正常的回复, 并且计数
    超过预期次数后, 需要重置所有的对话.
    """

    def new(self, ctx: Context) -> CtxPipe:
        # todo: 需要实现
        return mock_pipe
