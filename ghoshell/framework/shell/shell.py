from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, Callable, List, Any, ClassVar

from ghoshell.container import Container, Provider
from ghoshell.messages import Input, Batch
from ghoshell.shell import Shell
from ghoshell.utils import create_pipeline

# input 处理管道
InputPipeline = Callable[
    [Input],
    Batch,
]

InputPipe = Callable[
    [Input, InputPipeline],
    Batch,
]

# output 处理管道
OutputPipeline = Callable[
    [Batch],
    Batch,
]

OutputPipe = Callable[
    [Batch, OutputPipeline],
    Batch,
]


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
    def parse_event(self, e: Any) -> Optional[Input]:
        pass

    @property
    def container(self) -> Container:
        return self._container

    # ----- implements ----- #

    def bootstrap(self) -> Shell:
        """
        初始化启动
        """
        for provider in self.get_providers():
            self._container.register(provider)

        self._container.register_meta_repos()

        for bootstrapper in self.get_bootstrapper():
            bootstrapper.bootstrap(self)
        return self

    # ----- async methods ----- #

    def handle_input(self, _input: Input) -> Batch:
        """
        用管道的方式来处理 input
        todo: try catch
        """
        try:
            pipes: List[InputPipe] = []
            for mdw in self.get_input_mdw():
                pipes.append(mdw.new_pipe(self))

            pipeline = create_pipeline(pipes, self._input_destination)
            batch = pipeline(_input)
            # 解决入参的 shell_env 封装问题.
            return batch
        finally:
            # todo ?
            pass

    def _input_destination(self, _input: Input) -> Batch:
        outputs = self.deliver(_input)
        batch = Batch(input=_input.model_dump())
        if outputs is not None:
            batch.outputs = outputs
        return batch

    def handle_outputs(self, batch: Batch) -> None:
        """
        用管道的形式处理输出
        """
        try:
            pipes: List[OutputPipe] = []
            for mdw in self.get_output_mdw():
                pipes.append(mdw.new_pipe(self))

            pipeline = create_pipeline(pipes, self._output_destination)

            final_batch = pipeline(batch)
            for _output in final_batch.outputs:
                self.output(_output, final_batch.input)
        # todo: exception handler
        finally:
            pass

    @staticmethod
    def _output_destination(batch: Batch) -> Batch:
        return batch

    def handle(self, e: Any) -> None:
        """
        响应一个普通事件.
        """
        try:
            # todo: 没有做正确的异常处理.
            _input = self.parse_event(e)
            if _input is None:
                # 默认无法处理的事件. 不做任何响应.
                return
            batch = self.handle_input(_input)
            self.handle_outputs(batch)
        finally:
            # todo: 异常处理
            pass

    @property
    def config_path(self) -> str:
        return self._config_path

    @property
    def runtime_path(self) -> str:
        return self._runtime_path
