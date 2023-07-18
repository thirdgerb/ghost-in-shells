from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Tuple, Optional, Callable, List, Any, ClassVar, Awaitable

from ghoshell.container import Container, Provider
from ghoshell.messages import Output, Input
from ghoshell.shell import Shell, Messenger
from ghoshell.utils import create_pipeline

# input 处理管道
InputPipeline = Callable[
    [Input],
    Awaitable[
        Tuple[
            Input,
            Optional[List[Output]]
        ]
    ]
]

InputPipe = Callable[
    [Input, InputPipeline],
    Awaitable[
        Tuple[
            Input,
            Optional[List[Output]]
        ]
    ]
]

# output 处理管道
OutputPipeline = Callable[[Output], Awaitable[Output]]

OutputPipe = Callable[[Output, OutputPipeline], Awaitable[Output]]


class ShellInputMdw(metaclass=ABCMeta):
    """
    shell 的输入中间件
    """

    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def new_pipe(self, shell: Shell) -> InputPipe:
        """
        初始化一个管道.
        """
        pass


class ShellOutputMdw(metaclass=ABCMeta):
    """
    shell 的输出中间件
    """

    def name(self) -> str:
        """
        中间件的名字
        """
        return self.__class__.__name__

    @abstractmethod
    def new_pipe(self, shell: Shell) -> OutputPipe:
        """
        初始化一个管道.
        mdw 应该要理解 context 的类型.
        """
        pass


class ShellBootstrapper(metaclass=ABCMeta):
    """
    用来自定义初始化逻辑.
    """

    def bootstrap(self, shell: Shell) -> None:
        """
        用来初始化 Shell.
        """
        pass


class ShellKernel(Shell, metaclass=ABCMeta):
    KIND: ClassVar[str] = "shell"

    def __init__(self, container: Container, config_path: str, runtime_path: str):
        self._container = Container(container)
        self._container.set(Shell, self)
        self._config_path = config_path
        self._runtime_path = runtime_path
        self._messenger: Messenger | None = None

    @property
    def kind(self) -> str:
        return self.KIND

    @abstractmethod
    def get_providers(self) -> List[Provider]:
        """
        Shell 启动时加载到 container 里的 provider
        """
        pass

    @abstractmethod
    def get_bootstrapper(self) -> List[ShellBootstrapper]:
        """
        Shell 启动时运行的方法.
        """
        pass

    @abstractmethod
    def get_input_mdw(self) -> List[ShellInputMdw]:
        """
        Shell 处理输入消息的中间件.
        """
        pass

    @abstractmethod
    def get_output_mdw(self) -> List[ShellOutputMdw]:
        """
        Shell 处理输出消息的中间件.
        """
        pass

    @abstractmethod
    def on_event(self, e: Any) -> Optional[Input]:
        pass

    @property
    def container(self) -> Container:
        return self._container

    def messenger(self, _input: Input | None) -> Messenger:
        if self._messenger is None:
            self._messenger = self._container.force_fetch(Messenger)
        return self._messenger

    # ----- implements ----- #

    def bootstrap(self) -> Shell:
        """
        初始化启动
        """
        for provider in self.get_providers():
            self._container.register(provider)

        for bootstrapper in self.get_bootstrapper():
            bootstrapper.bootstrap(self)
        return self

    # ----- async methods ----- #

    @abstractmethod
    async def deliver(self, _output: Output) -> None:
        """
        发送输出消息.
        """
        pass

    async def on_input(self, _input: Input) -> Tuple[Input, List[Output] | None]:
        """
        用管道的方式来处理 input
        todo: try catch
        """
        try:
            pipes: List[InputPipe] = []
            for mdw in self.get_input_mdw():
                pipes.append(mdw.new_pipe(self))

            async def destination(_input: Input) -> Tuple[Input, List[Output] | None]:
                return _input, None

            pipeline = create_pipeline(pipes, destination)
            _input, _outputs = await pipeline(_input)
            # 解决入参的 shell_env 封装问题.
            return _input, _outputs
        finally:
            # todo ?
            pass

    async def on_output(self, _output: Output) -> None:
        """
        用管道的形式处理输出
        """
        try:
            pipes: List[OutputPipe] = []
            for mdw in self.get_output_mdw():
                pipes.append(mdw.new_pipe(self))

            async def destination(__output: Output) -> Output:
                return __output

            pipeline = create_pipeline(pipes, destination)
            final_output = await pipeline(_output)
            await self.deliver(final_output)
        # todo: exception handler
        finally:
            pass

    async def listen_async_output(self) -> None:
        try:
            await self._messenger.await_async_output(self.on_output)
        # todo exception
        finally:
            pass

    async def tick(self, e: Any) -> None:
        """
        响应一个普通事件.
        """
        try:
            # todo: 没有做正确的异常处理.
            _input = self.on_event(e)
            if _input is None:
                # 默认无法处理的事件. 不做任何响应.
                return
            _input, _outputs = await self.on_input(_input)
            if _outputs is not None:
                # 被拦截了.
                for _output in _outputs:
                    await self.on_output(_output)
                return

            # 发送给 Ghost
            messenger = self.messenger(_input)
            _outputs = await messenger.send(_input)
            if _outputs is None:
                # 为 None 时表示服务端没有返回消息.
                return
            else:
                for _output in _outputs:
                    await self.on_output(_output)
                return
        finally:
            # todo: 异常处理
            pass

    @property
    def config_path(self) -> str:
        return self._config_path

    @property
    def runtime_path(self) -> str:
        return self._runtime_path
