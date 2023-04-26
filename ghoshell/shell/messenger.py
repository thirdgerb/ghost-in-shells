from abc import ABCMeta, abstractmethod
from typing import List, Callable, Optional

from ghoshell.messages.io import Input, Output


class Messenger(metaclass=ABCMeta):

    @abstractmethod
    def send(self, _input: Input) -> Optional[List[Output]]:
        """
        发送一则同步消息. Ghost 基本上只能处理同步协议.
        Shell 来解决双工或异步问题.
        """
        pass

    @abstractmethod
    def send_async_input(self, _input: Input) -> None:
        """
        发送一个异步消息.
        """
        pass

    @abstractmethod
    async def await_async_output(self, handler: Callable[[Output], None]) -> None:
        pass
