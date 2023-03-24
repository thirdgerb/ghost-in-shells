from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Tuple, Optional, Any

from ghoshell.ghost import Ghost, Input, Output


class IShellContext(metaclass=ABCMeta):
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
        """
        shell 的类型
        """
        pass

    @abstractmethod
    def bootstrap(self) -> IShell:
        """
        对 shell 进行初始化
        通常是 shell.bootstrap().run()
        """
        pass

    @abstractmethod
    def connect(self, _input: Input) -> Ghost:
        """
        shell 需要有联系 ghost 的能力
        有可能是一对多的, 简单情况下一个 shell 与一个 ghost 强对应.
        """
        pass

    def context(self, _input: Input) -> IShellContext:
        """
        根据 Input 生成 Context.
        """
        pass

    @abstractmethod
    def on_event(self, event: Any) -> Optional[Input]:
        """
        收到一个事件时, 可以初始化一个 shell 的 context
        """
        pass

    @abstractmethod
    def on_input(self, _input: Input) -> Tuple[Input, Optional[Output]]:
        """
        响应 shell 的输入事件.
        """
        pass

    @abstractmethod
    def on_output(self, _output: Output) -> None:
        """
        得到一个 shell 的输出 (同步或异步)
        需要有能力将之发送给用户.
        """
        pass

    @abstractmethod
    def run(self):
        """
        将 shell 作为一个 app 来运行.
        """
        pass
