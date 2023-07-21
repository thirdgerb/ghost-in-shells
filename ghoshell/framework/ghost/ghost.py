from __future__ import annotations

import traceback
import uuid
from abc import ABCMeta, abstractmethod
from typing import Callable, List

from ghoshell.container import Container, Provider
from ghoshell.contracts import Cache, APIRepository
from ghoshell.framework.contracts.think_meta_storage import ThinkMetaStorage
from ghoshell.framework.ghost import providers
from ghoshell.framework.ghost.clone import CloneImpl
from ghoshell.framework.ghost.config import GhostConfig
from ghoshell.framework.ghost.context import ContextImpl
from ghoshell.framework.ghost.middleware import CtxMiddleware, CtxPipe, CtxPipeline
from ghoshell.framework.ghost.middleware import ExceptionHandlerMiddleware, ProcessLockerMiddleware
from ghoshell.ghost import CloneError, BootstrapError, GhostError, ContextError
from ghoshell.ghost import Ghost, Clone, Context, OperationKernel
from ghoshell.ghost import Mindset, Focus, Memory
from ghoshell.messages import Input, Output, ErrMsg
from ghoshell.utils import create_pipeline


class GhostBootstrapper(metaclass=ABCMeta):

    @abstractmethod
    def bootstrap(self, ghost: Ghost):
        pass


class GhostKernel(Ghost, metaclass=ABCMeta):
    """
    Ghost 框架实现的内核
    """

    def __init__(
            self,
            container: Container,
            config: GhostConfig,
            config_path: str,
            runtime_path: str,
    ):
        self._config = config
        self._container = container
        self._mindset: Mindset | None = None
        self._focus: Focus | None = None
        self._memory: Memory | None = None
        self._config_path = config_path
        self._runtime_path = runtime_path
        container.set(Ghost, self)
        container.set(GhostConfig, config)
        # self._messenger: Messenger = messenger

    def boostrap(self) -> "Ghost":
        self._init_container()
        # bootstrapper
        for boot in self.get_bootstrapper():
            boot.bootstrap(self)

        for depending in self.get_depending_contracts():
            if not self._container.bound(depending):
                raise BootstrapError(f"ghost depending contract {depending} is not bound")
        return self

    def _init_container(self):
        self._container.set(Ghost, self)
        self._container.set(GhostConfig, self._config)

        for provider in self.get_ghost_providers():
            self._container.register(provider)

        for provider in self.get_contracts_providers():
            self._container.register(provider)

        # all meta repository shall be registered
        self._container.register_meta_repos()

    # ---- 配置类函数 ---- #

    def get_bootstrapper(self) -> List[GhostBootstrapper]:
        return []

    def get_context_middleware(self) -> List[CtxMiddleware]:
        """
        上下文相关的中间件.
        """
        return [
            ExceptionHandlerMiddleware(),
            ProcessLockerMiddleware(),
        ]

    def get_depending_contracts(self) -> List:
        """
        用来检查容器里是否实现了绑定.
        """
        return [
            Cache,
            ThinkMetaStorage,
            APIRepository,
            GhostConfig,
        ]

    def get_contracts_providers(self) -> List[Provider]:
        """
        与 Ghost 无关的各种 providers.
        """
        return []

    def get_context_providers(self) -> List[Provider]:
        """
        context 初始化时才执行的 providers
        """
        return [
            providers.ContextLoggerProvider(),
            providers.SessionProvider(),
            providers.RuntimeProvider(),
        ]

    def get_ghost_providers(self) -> List[Provider]:
        """
        ghost 启动的时候执行的 providers
        """
        return [
            providers.MindsetProvider(),
            providers.FocusProvider(),
            providers.MemoryProvider(),
        ]

    # ---- abstract ---- #

    def new_context(self, inpt: Input) -> Context:
        """
        机器人构建上下文, 最核心的能力
        """
        if not inpt.trace.clone_id:
            raise CloneError("todo xxxx")

        clone = self.new_clone(inpt.trace.clone_id)
        ctx_container = Container(self._container)
        ctx_container.set(Clone, clone)
        # instance
        ctx = ContextImpl(
            inpt=inpt,
            clone=clone,
            container=ctx_container,
            config=self._config
        )
        for provider in self.get_context_providers():
            ctx_container.register(provider)
        return ctx

    def new_operation_kernel(self) -> "OperationKernel":
        return self.container.force_fetch(OperationKernel)

    def respond(self, inpt: Input) -> List[Output] | None:
        """
        核心方法: 处理输入 inpt
        """
        try:
            ctx = self.new_context(inpt)
            return self._react(ctx)
        except Exception as e:
            self._fail(e)
        finally:
            # todo: handle exception
            pass

    def _fail(self, e: Exception) -> None:
        print("\n".join(traceback.format_exception(e)))
        exit(1)

    def _react(self, ctx: Context) -> List[Output]:
        """
        因为需要两层 try catch, 所以拆分一个内部方法.
        """
        try:
            pipeline = self._build_pipeline()
            ctx = pipeline(ctx)

            return ctx.get_unsent_outputs()
        except ContextError as e:
            # todo
            return [self._failure_message(_input=ctx.input, err=e)]
        except CloneError as e:
            ctx.on_fatal(e)
            return [self._failure_message(_input=ctx.input, err=e)]

        finally:
            ctx.finish()

    @classmethod
    def _failure_message(cls, _input: Input, err: GhostError) -> Output:
        stack_info = "\n".join(traceback.format_exception(err))
        msg = ErrMsg(errcode=err.CODE, errmsg=str(err), stack_info=stack_info)
        _output = Output.new(uuid.uuid4().hex, _input)
        msg.join(_output.payload)
        return _output

    @property
    def name(self) -> str:
        return self._config.name

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
        pipes: List[CtxPipe] = []
        # 用 run 方法组成 pipes
        for m in self.get_context_middleware():
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
            op = kernel.init_operator()
            kernel.run_dominos(ctx, op)
            # 记得随手清空对象, 避免内存泄漏
            kernel.destroy()
            return ctx

        return destination

    @property
    def config_path(self) -> str:
        return self._config_path

    @property
    def runtime_path(self) -> str:
        return self._runtime_path
