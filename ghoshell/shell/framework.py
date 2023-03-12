from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Tuple, Optional, Any, Callable, List

from ghoshell.ghost import Output, Input, IGhost
from ghoshell.shell import IShell, IContext
from ghoshell.utils import create_pipeline

# input 处理管道
INPUT_PIPELINE = Callable[[Input], Tuple[Input, Optional[Output]]]
INPUT_PIPE = Callable[[Input, INPUT_PIPELINE], Tuple[Input, Optional[Output]]]

# output 处理管道
OUTPUT_PIPELINE = Callable[[Output], Output]
OUTPUT_PIPE = Callable[[Output, OUTPUT_PIPELINE], Output]


class InputMiddleware(metaclass=ABCMeta):
    """
    shell 的输入中间件
    """

    @abstractmethod
    def name(self) -> str:
        """
        中间件的名字, 用来做记录?
        """
        pass

    @abstractmethod
    def new(self, ctx: IContext) -> INPUT_PIPE:
        """
        初始化一个管道.
        """
        pass


class OutputMiddleware(metaclass=ABCMeta):
    """
    shell 的输出中间件
    """

    @abstractmethod
    def name(self) -> str:
        """
        中间件的名字
        """
        pass

    @abstractmethod
    def new(self, ctx: IContext) -> OUTPUT_PIPE:
        """
        初始化一个管道.
        mdw 应该要理解 context 的类型.
        """
        pass


class Bootstrapper(metaclass=ABCMeta):
    """
    用来自定义初始化逻辑.
    """

    def bootstrap(self, shell: IShell) -> None:
        pass


class ShellFramework(IShell, metaclass=ABCMeta):
    # 初始化流程
    bootstrapping: List[Bootstrapper] = []
    # 输入处理
    input_middleware: List[InputMiddleware] = []
    # 输出处理
    output_middleware: List[OutputMiddleware] = []

    @abstractmethod
    def connect(self, inpt: Input) -> IGhost:
        pass

    @abstractmethod
    def on_event(self, e: Any) -> Input:
        """
        在 shell 接受到事件时, 需要为事件创建 context
        """
        pass

    @abstractmethod
    def context(self, _input: Input) -> IContext:
        pass

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def run(self):
        """
        运行服务
        """
        pass

    def boostrap(self) -> ShellFramework:
        """
        初始化启动
        """
        for bootstrapper in self.bootstrapping:
            bootstrapper.bootstrap(self)
        return self

    def tick(self, event: Any) -> None:
        """
        shell 响应单个事件
        """
        try:
            _input = self.on_event(event)
            _input, _output = self._on_input(_input)
            if _output is None:
                ghost = self.connect(_input)
                _output = ghost.react(_input)
            self._on_output(_output)
        finally:
            pass

    # ----- inner methods ----- #

    def _on_input(self, _input: Input) -> Tuple[Input, Optional[Output]]:
        """
        用管道的方式来处理 input
        todo: try catch
        """

        ctx = self.context(_input)
        try:
            pipes: List[INPUT_PIPE] = []
            for mdw in self.input_middleware:
                pipes.append(mdw.new(ctx))

            def destination(_input: Input) -> Tuple[Input, Optional[Output]]:
                return _input, None

            pipeline = create_pipeline(pipes, destination)
            _input, _output = pipeline(_input)
            return _input, _output
        finally:
            ctx.destroy()

    def _on_output(self, output: Output) -> None:
        """
        用管道的形式处理输出
        """
        ctx = self.context(output.input)
        try:
            pipes: List[OUTPUT_PIPE] = []
            for mdw in self.output_middleware:
                pipes.append(mdw.new(ctx))

            def destination(_output: Output) -> Output:
                return _output

            pipeline = create_pipeline(pipes, destination)
            final_output = pipeline(output)
            ctx.send(final_output)
        finally:
            ctx.destroy()
