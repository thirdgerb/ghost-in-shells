import sys
import traceback
import uuid
from abc import ABCMeta, abstractmethod
from typing import Callable, List

from ghoshell.container import Container, Provider
from ghoshell.contracts import Cache
from ghoshell.ghost import Ghost, Clone, Context, OperationKernel
from ghoshell.ghost import Mindset, Focus, Memory
from ghoshell.ghost import RuntimeException, GhostException
from ghoshell.ghost_fmk.clone import CloneImpl
from ghoshell.ghost_fmk.config import GhostConfig
from ghoshell.ghost_fmk.context import ContextImpl
from ghoshell.ghost_fmk.contracts import ThinkMetaDriver
from ghoshell.ghost_fmk.middleware import CtxMiddleware, ExceptionHandlerMiddleware, CtxPipe, CtxPipeline
from ghoshell.ghost_fmk.providers import CacheRuntimeDriverProvider, MindsetProvider, FocusProvider, MemoryProvider
from ghoshell.messages import Input, Output, ErrMsg
from ghoshell.utils import create_pipeline


class Bootstrapper(metaclass=ABCMeta):

    @abstractmethod
    def bootstrap(self, ghost: Ghost):
        pass


class GhostKernel(Ghost, metaclass=ABCMeta):
    """
    Ghost 框架实现的内核
    """

    # 启动流程. 想用这种方式解耦掉系统文件读取等逻辑.
    bootstrapper: List[Bootstrapper] = []

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
        for boot in self.bootstrapper:
            boot.bootstrap(self)

        for depending in self._depend_contracts():
            if not self._container.bound(depending):
                raise GhostException(f"ghost depending contract {depending} is not bound")
        return self

    def _init_container(self):
        self._container.set(Ghost, self)
        self._container.set(GhostConfig, self._config)
        for provider in self._ghost_providers():
            self._container.register(provider)
        for provider in self._contracts_providers():
            self._container.register(provider)

    @classmethod
    def _context_middleware(cls) -> List[CtxMiddleware]:
        return [
            ExceptionHandlerMiddleware(),
        ]

    @classmethod
    def _depend_contracts(cls) -> List:
        return [
            Cache,
            ThinkMetaDriver,
        ]

    @classmethod
    @abstractmethod
    def _contracts_providers(cls) -> List[Provider]:
        pass

    @classmethod
    @abstractmethod
    def _context_providers(cls) -> List[Provider]:
        """
        context 初始化时执行的 providers
        """
        pass

    def _ghost_providers(self) -> List[Provider]:
        """
        ghost 启动的时候执行的 providers
        """
        return [
            CacheRuntimeDriverProvider(),
            MindsetProvider(),
            FocusProvider(),
            MemoryProvider(),
        ]

    # ---- abstract ---- #

    def new_context(self, inpt: Input) -> Context:
        """
        机器人构建上下文, 最核心的能力
        """
        if not inpt.trace.clone_id:
            raise RuntimeException("todo xxxx")

        clone = self.new_clone(inpt.trace.clone_id)
        ctx_container = Container(self._container)
        # instance
        ctx = ContextImpl(
            inpt=inpt,
            clone=clone,
            container=ctx_container,
            config=self._config
        )
        # bound instances
        ctx_container.set(Clone, clone)
        ctx_container.set(Context, ctx)
        for provider in self._context_providers():
            ctx_container.register(provider)
        return ctx

    @abstractmethod
    def new_operation_kernel(self) -> "OperationKernel":
        pass

    def respond(self, inpt: Input) -> List[Output] | None:
        """
        核心方法: 处理输入 inpt
        """
        try:
            ctx = self.new_context(inpt)
            return self._react(ctx)
        except GhostException as e:
            return [self._failure_message(_input=inpt, err=e)]
        except Exception as e:
            ex = GhostException(message=e.__repr__())
            return [self._failure_message(_input=inpt, err=ex)]
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
        except GhostException as e:
            ctx.fail()
            return [self._failure_message(_input=ctx.input, err=e)]
        finally:
            ctx.finish()

    @classmethod
    def _failure_message(cls, _input: Input, err: GhostException) -> Output:
        stack_info = err.stack_info
        if not stack_info:
            stack_info = "\n".join(traceback.format_exception(*sys.exc_info(), limit=5))
        msg = ErrMsg(errcode=err.CODE, errmsg=str(err), at=err.at, stack_info=stack_info)
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
        for m in self._context_middleware():
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

    @property
    def config_path(self) -> str:
        return self._config_path

    @property
    def runtime_path(self) -> str:
        return self._runtime_path
