from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Tuple, Optional, Any

from ghoshell.container import Container
from ghoshell.messages import Input, Output
from ghoshell.shell.messenger import Messenger


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
    def messenger(self, _input: Input | None) -> Messenger:
        """
        shell 需要有联系 ghost 的能力
        有可能是一对多的, 简单情况下一个 shell 与一个 ghost 强对应.
        """
        pass

    @abstractmethod
    def on_event(self, event: Any) -> Optional[Input]:
        """
        收到一个事件时, 可以初始化一个 shell 的 context
        """
        pass

    @abstractmethod
    def tick(self, e: Any) -> None:
        """
        处理单个 shell 事件. 同步逻辑.
        """
        pass

    @abstractmethod
    def on_input(self, _input: Input) -> Tuple[Input, Optional[Output]]:
        """
        响应 shell 的输入事件.
        """
        pass

    @abstractmethod
    def on_output(self, _outputs: Output) -> None:
        """
        得到一个 shell 的输出 (同步或异步)
        需要有能力将之发送给用户.
        """
        pass

    @abstractmethod
    async def listen_async_output(self) -> None:
        """
        处理异步消息的逻辑. 可以放到 loop 里实现.
        """
        pass

    @abstractmethod
    def run_as_app(self) -> None:
        """
        当成 app 来执行.
        """
        pass

    @property
    @abstractmethod
    def config_path(self) -> str:
        pass

    @property
    @abstractmethod
    def runtime_path(self) -> str:
        pass
