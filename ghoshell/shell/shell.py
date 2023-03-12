from __future__ import annotations

from abc import ABCMeta, abstractmethod

from ghoshell.ghost import Input, Output


class IContext(metaclass=ABCMeta):
    """
    shell 的上下文
    """

    @abstractmethod
    def send(self, _output: Output) -> None:
        """
        发送一个 ghost 的输出.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        清空上下文信息, 做后续的处理
        """
        pass


class IShell(metaclass=ABCMeta):

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def bootstrap(self) -> IShell:
        pass

    @abstractmethod
    def context(self, _input: Input) -> IContext:
        pass

    @abstractmethod
    def run(self):
        pass
