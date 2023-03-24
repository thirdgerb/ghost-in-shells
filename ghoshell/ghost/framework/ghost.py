from abc import ABCMeta, abstractmethod
from typing import Callable, List, Dict, Optional

from ghoshell.ghost import Ghost, Input, Output, Context, Operator
from ghoshell.ghost.framework.middleware import IMiddleware, ExceptionHandlerMiddleware, GHOST_PIPE, GHOST_PIPELINE
from ghoshell.ghost.framework.runtime import IRuntimeDriver
from ghoshell.utils import create_pipeline


class GhostKernel(Ghost, metaclass=ABCMeta):
    """
    Ghost 框架实现的内核
    """

    # ghost 运行各种中间件.
    middleware: List[IMiddleware] = [
        ExceptionHandlerMiddleware(),
    ]

    # --- 以下是各种 driver 的实现 --- #

    runtime_driver: IRuntimeDriver

    def react(self, inpt: Input) -> Output:
        """
        核心方法: 处理输入 inpt
        """
        try:
            ctx = self._new_context(inpt)
            return self._react(ctx, inpt)
        finally:
            # todo: handle exception
            pass

    def _react(self, ctx: Context, inpt: Input) -> Output:
        """
        因为需要两层 try catch, 所以拆分一个内部方法.
        """
        try:
            pipeline = self._build_pipeline(ctx)
            output = pipeline(inpt)
            # 输出时携带 ghost 的场景协议.
            # 默认用 {} 来实现就可以了.
            output.ghost_env = self.ghost_env(ctx)
            return output
        finally:
            ctx.destroy()

    @abstractmethod
    def ghost_env(self, ctx: Context) -> Dict:
        """
        根据上下文返回 ghost 定义的 env 协议.
        """
        pass

    # ---- abstract ---- #

    @abstractmethod
    def _new_context(self, inpt: Input) -> Context:
        """
        机器人构建上下文, 最核心的能力
        """
        pass

    @abstractmethod
    def _failed(self, inpt: Input) -> Output:
        """
        解决异常问题
        """
        pass

    def _init_operator(self, inpt: Input) -> Operator:
        """
        初始化算子
        """
        pass

    # ---- 内部方法 ---- #

    def _build_pipeline(self, ctx: Context) -> Callable[[Input], Output]:
        """
        使用中间件实现一个管道
        """
        middleware = self.middleware if self.middleware else []
        pipes: List[GHOST_PIPE] = []
        # 用 run 方法组成 pipes
        for m in middleware:
            pipe = m.new(ctx)
            pipes.append(pipe)
        # 返回 pipeline
        return create_pipeline(pipes, self._build_destination(ctx))

    def _build_destination(self, ctx: Context) -> GHOST_PIPELINE:
        """
        实现管道的最后一环.
        运行各种算子.
        """

        def destination(_input: Input) -> Optional[Output]:
            ctx.set_input(_input)
            # 实例化一个上下文级别的 operator manager.
            # 用于解决 stack overflow 等问题.
            manager = ctx.new_operator_manager()
            manager.run_dominos(ctx, self._init_operator(_input))
            # 记得随手清空对象, 避免内存泄漏
            manager.destroy()
            return ctx.gen_output()

        return destination
