from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, Any, List

from ghoshell.container import Container
from ghoshell.messages import Input, Output, Batch


class Shell(metaclass=ABCMeta):

    @property
    @abstractmethod
    def kind(self) -> str:
        """
        shell 的类型
        """
        pass

    @property
    @abstractmethod
    def container(self) -> Container:
        pass

    @abstractmethod
    def bootstrap(self) -> Shell:
        """
        对 shell 进行初始化
        通常是 shell.bootstrap().run()
        """
        pass

    @abstractmethod
    def deliver(self, _input: Input) -> List[Output] | None:
        """
        发送消息给 Ghost.
        """
        pass

    @abstractmethod
    def parse_event(self, event: Any) -> Optional[Input]:
        """
        收到一个事件时, 可以初始化一个 Input 消息
        """
        pass

    @abstractmethod
    def handle(self, e: Any) -> None:
        """
        处理单个 shell 事件.
        """
        pass

    @abstractmethod
    def handle_input(self, _input: Input) -> Batch:
        """
        响应 shell 的输入事件, 可以对 Input 进行加工.
        加工后, 如果 Input == None, 则意味着它被处理没了.
        """
        pass

    @abstractmethod
    def handle_outputs(self, batch: Batch) -> None:
        """
        处理一个 shell 的输出 (同步或异步)
        """
        pass

    @abstractmethod
    def output(self, _output: Output, _input: Input) -> None:
        """
        输出一个消息.
        """
        pass

    @abstractmethod
    def run_as_app(self) -> None:
        """
        需要实现功能, 使之可以当成 app 来执行.
        但有些情况下也许只要用到 on_input 或者 on_output
        """
        pass

    @property
    @abstractmethod
    def config_path(self) -> str:
        """
        shell 启动时的配置路径
        """
        pass

    @property
    @abstractmethod
    def runtime_path(self) -> str:
        """
        shell 运行时的路径.
        """
        pass
