from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Tuple, Optional, Callable, List, Any, Dict

from ghoshell.ghost import Output, Input
from ghoshell.shell.shell import IShell, IShellContext
from ghoshell.utils import create_pipeline

# input 处理管道
INPUT_PIPELINE = Callable[[Input], Tuple[Input, Optional[Output]]]
INPUT_PIPE = Callable[[Input, INPUT_PIPELINE], Tuple[Input, Optional[Output]]]

# output 处理管道
OUTPUT_PIPELINE = Callable[[Output], Output]
OUTPUT_PIPE = Callable[[Output, OUTPUT_PIPELINE], Output]

EVENT_PIPELINE = Callable[[Any], Optional[Input]]
EVENT_PIPE = Callable[[Any, EVENT_PIPELINE], Optional[Input]]


class EventMiddleware(metaclass=ABCMeta):
    """
    shell 响应事件, 生成 Input 的逻辑.
    """

    @abstractmethod
    def new(self, shell: IShell) -> EVENT_PIPE:
        """
        初始化一个管道.
        """
        pass


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
    def new(self, ctx: IShellContext) -> INPUT_PIPE:
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
    def new(self, ctx: IShellContext) -> OUTPUT_PIPE:
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
        """
        用来初始化 Shell.
        """
        pass


class ShellKernel(IShell, metaclass=ABCMeta):
    # 初始化流程
    bootstrapping: List[Bootstrapper] = []

    # 事件处理中间件.
    event_middleware: List[EventMiddleware] = []

    # 输入处理
    input_middleware: List[InputMiddleware] = []
    # 输出处理
    output_middleware: List[OutputMiddleware] = []

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def run(self):
        """
        运行服务
        """
        pass

    def on_event(self, e: Any) -> Optional[Input]:
        """
        响应事件, 生成 Context
        事件通常来自 shell
        """
        pipes: List[EVENT_PIPE] = []
        for mdw in self.event_middleware:
            pipes.append(mdw.new(self))

        def destination(event) -> Optional[Input]:
            """
            默认无法响应.
            """
            return None

        pipeline = create_pipeline(pipes, destination)
        return pipeline(e)

    # ----- implements ----- #

    def bootstrap(self) -> IShell:
        """
        初始化启动
        """
        for bootstrapper in self.bootstrapping:
            bootstrapper.bootstrap(self)
        return self

    # ----- inner methods ----- #

    def on_input(self, _input: Input) -> Tuple[Input, Optional[Output]]:
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
            # 解决入参的 shell_env 封装问题.
            _input.shell_env = self.shell_env(ctx)
            return _input, _output
        finally:
            ctx.destroy()

    @abstractmethod
    def shell_env(self, ctx: IShellContext) -> Dict:
        pass

    def on_output(self, output: Output) -> None:
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

    def tick(self, e: Any) -> None:
        """
        响应一个普通事件.
        """
        try:
            _input = self.on_event(e)
            if _input is None:
                # 默认无法处理的事件. 不做任何响应.
                return
            _input, _output = self.on_input(_input)
            if _output is None:
                ghost = self.connect(_input)
                _output = ghost.react(_input)
            self.on_output(_output)
        finally:
            # todo: 异常处理
            pass
