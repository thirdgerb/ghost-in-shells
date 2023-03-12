from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

from ghoshell.ghost import IGhost
from ghoshell.utils import create_pipeline

if TYPE_CHECKING:
    from typing import Callable, List, Dict
    from ghoshell.ghost.io import Input, Output
    from ghoshell.ghost.context import IContext
    from ghoshell.ghost.operator import IOperator

from ghoshell.ghost.framework.runtime import IRuntimeDriver

GHOST_PIPE = Callable[[Input], Output]


class IMiddleware(metaclass=ABCMeta):
    """
    组件
    """

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def run(self, inpt: Input, next_fn: GHOST_PIPE) -> Output:
        pass


class Ghost(IGhost, metaclass=ABCMeta):
    middleware: List[IMiddleware]
    runtime_driver: IRuntimeDriver

    def react(self, inpt: Input) -> Output:
        """
        核心方法: 处理输入 inpt
        """
        try:
            pipeline = self._build_pipeline()
            output = pipeline(inpt)
            return output
        finally:
            return self._failed(inpt)

    def output_env(self, ctx: IContext) -> Dict:
        """
        根据上下文返回 env 协议.
        """
        return {}

    # ---- abstract ---- #

    @abstractmethod
    def _new_context(self, inpt: Input) -> IContext:
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

    def _init_operator(self, inpt: Input) -> IOperator:
        """
        初始化算子
        """
        pass

    # ---- 内部方法 ---- #

    def _do_handle(self, inpt: Input) -> Output:
        ctx = self._new_context(inpt)
        op = self._init_operator(inpt)

        # 伪代码, 真实运行时 op 要做复杂的改造.
        while op:
            op = op.run(ctx)

        return ctx.output()

    def _build_pipeline(self) -> Callable[[Input], Output]:
        """
        使用中间件实现一个管道
        """
        middleware = self.middleware if self.middleware else []
        pipes = []
        # 用 run 方法组成 pipes
        for m in middleware:
            pipe = self._mdw_pipe(m)
            pipes.append(pipe)
        # 返回
        return create_pipeline(pipes, self._do_handle)

    def _mdw_pipe(self, mdw: IMiddleware) -> GHOST_PIPE:
        """
        可以再包一层, 方便做日志, 错误捕获的封装.
        """
        return mdw.run
