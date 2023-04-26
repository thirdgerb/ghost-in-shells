from abc import ABCMeta, abstractmethod
from typing import Callable, List

from ghoshell.container import Container, Provider
from ghoshell.ghost import Ghost, Clone, Context, OperationKernel
from ghoshell.ghost import Mindset, Focus, Memory
from ghoshell.ghost import RuntimeException
from ghoshell.ghost_fmk.clone import CloneImpl
from ghoshell.ghost_fmk.config import GhostConfig
from ghoshell.ghost_fmk.context import ContextImpl
from ghoshell.ghost_fmk.middleware import CtxMiddleware, ExceptionHandlerMiddleware, CtxPipe, CtxPipeline
from ghoshell.messages import Input, Output
from ghoshell.utils import create_pipeline


class Bootstrapper(metaclass=ABCMeta):

    @abstractmethod
    def bootstrap(self, ghost: Ghost):
        pass


class GhostKernel(Ghost, metaclass=ABCMeta):
    """
    Ghost 框架实现的内核
    """

    # ghost 初始化时, 向 ioc 容器注册.
    providers: List[Provider] = []

    # 启动流程. 想用这种方式解耦掉系统文件读取等逻辑.
    bootstrapper: List[Bootstrapper] = []

    # 初始化 context 时, 注册到 context 级别的 ioc
    context_providers: List[Provider] = []

    # ghost 运行各种中间件.
    middleware: List[CtxMiddleware] = [
        ExceptionHandlerMiddleware(),
    ]

    def __init__(
            self,
            name: str,
            container: Container,
            root_path: str,
            config: GhostConfig,
            # messenger: Messenger,
    ):
        self._name = name
        self._root_path = root_path
        self._config = config
        self._container = container
        self._mindset: Mindset | None = None
        self._focus: Focus | None = None
        self._memory: Memory | None = None
        # self._messenger: Messenger = messenger

    def boostrap(self) -> "Ghost":
        self._init_container()
        # bootstrapper
        for boot in self.bootstrapper:
            boot.bootstrap(self)

        # 注册所有的 provider
        for provider in self.providers:
            self._container.register(provider)
        return self

    def _init_container(self):
        self._container.set(Ghost, self)
        self._container.set(GhostConfig, self._config)
        for provider in self.providers:
            self._container.register(provider)

    # ---- abstract ---- #

    def new_context(self, inpt: Input) -> Context:
        """
        机器人构建上下文, 最核心的能力
        """
        if not inpt.trace.clone_id:
            raise RuntimeException("todo xxxx")

        clone = self.new_clone(inpt.trace.clone_id)
        container = Container(self._container)
        # instance
        ctx = ContextImpl(
            inpt=inpt,
            clone=clone,
            container=container,
            config=self._config
        )
        # bound instances
        container.set(Clone, clone)
        container.set(Context, ctx)
        for provider in self.context_providers:
            container.register(provider)
        return ctx

    @abstractmethod
    def new_operation_kernel(self) -> "OperationKernel":
        pass

    def app_path(self) -> str:
        return self._root_path

    def respond(self, inpt: Input) -> List[Output] | None:
        """
        核心方法: 处理输入 inpt
        """
        try:
            ctx = self.new_context(inpt)
            return self._react(ctx)
        except Exception:
            return None
        finally:
            # todo: handle exception
            pass

    def _react(self, ctx: Context) -> List[Output]:
        """
        因为需要两层 try catch, 所以拆分一个内部方法.
        """
        try:
            pipeline = self._build_pipeline()
            ctx = pipeline(ctx)
            return ctx.get_outputs()
        finally:
            ctx.finish()

    @property
    def name(self) -> str:
        return self._name

    @property
    def container(self) -> "Container":
        return self._container

    @property
    def mindset(self) -> "Mindset":
        if self._mindset is None:
            mindset = self._container.force_fetch(Mindset)
            self._mindset = mindset
        return self._mindset

    @property
    def focus(self) -> "Focus":
        if self._focus is None:
            self._focus = self._container.force_fetch(Focus)
        return self._focus

    @property
    def memory(self) -> "Memory":
        if self._memory is None:
            self._memory = self._container.force_fetch(Memory)
        return self._memory

    def new_clone(self, clone_id: str) -> "Clone":
        return CloneImpl(
            self,
            clone_id,
            self._config,
        )

    # ---- 内部方法 ---- #

    def _build_pipeline(self) -> Callable[[Context], Context]:
        """
        使用中间件实现一个管道
        """
        middleware = self.middleware if self.middleware else []
        pipes: List[CtxPipe] = []
        # 用 run 方法组成 pipes
        for m in middleware:
            pipe = m.new(self)
            pipes.append(pipe)
        # 返回 pipeline
        return create_pipeline(pipes, self._build_destination())

    def _build_destination(self) -> CtxPipeline:
        """
        实现管道的最后一环.
        运行各种算子.
        """

        def destination(ctx: Context) -> Context:
            # 实例化一个上下文级别的 operator manager.
            # 用于解决 stack overflow 等问题.
            kernel = self.new_operation_kernel()
            kernel.run_dominos(ctx, kernel.init_operator())
            # 记得随手清空对象, 避免内存泄漏
            kernel.destroy()
            return ctx

        return destination
