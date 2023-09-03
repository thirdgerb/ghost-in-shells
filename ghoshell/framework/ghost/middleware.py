from abc import ABCMeta, abstractmethod
from typing import Callable

from ghoshell.framework.ghost.config import GhostConfig
from ghoshell.ghost import Context, Ghost
from ghoshell.ghost import ContextError, BusyError, UnexpectedError

CtxPipeline = Callable[[Context], Context]
CtxPipe = Callable[[Context, CtxPipeline], Context]


class CtxMiddleware(metaclass=ABCMeta):
    """
    ctx 运行时的中间件.
    """

    @abstractmethod
    def new(self, ghost: Ghost) -> CtxPipe:
        pass


def mock_pipe(_input: Context, after: CtxPipeline) -> Context:
    return after(_input)


class ProcessLockerMiddleware(CtxMiddleware):

    def new(self, ghost: Ghost) -> CtxPipe:
        config = ghost.container.force_fetch(GhostConfig)

        def pipe(ctx: Context, after: CtxPipeline) -> Context:
            runtime = ctx.runtime
            process_id = runtime.current_process_id
            locked = False
            try:
                locked = runtime.lock_process(process_id)
                # lock failed
                if not locked:
                    raise BusyError(f"lock process {process_id} failed")

                return after(ctx)
            finally:
                if locked:
                    runtime.unlock_process(process_id)

        return pipe


class ExceptionHandlerMiddleware(CtxMiddleware):
    """
    全局处理异常的中间件.
    需要将会话异常处理成正常的回复, 并且计数
    超过预期次数后, 需要重置所有的对话.
    """

    def new(self, ghost: Ghost) -> CtxPipe:
        config = ghost.container.force_fetch(GhostConfig)

        def pipe(ctx: Context, after: CtxPipeline) -> Context:
            try:
                return after(ctx)
            except SystemError:
                raise
            except BusyError as e:
                ctx.logger.info(e)
                ctx.send_at(None).text(config.on_busy)
            except UnexpectedError as e:
                ctx.logger.info(e)
                ctx.send_at(None).err(config.on_unexpected)
            except ContextError as e:
                ctx.logger.info(e)
                ctx.send_at(None).err(e.message, e.CODE)
            return ctx
            # todo: 建立更好的 context 处理原则.

        return pipe
