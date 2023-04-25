from abc import ABCMeta, abstractmethod
from typing import List, Callable

from ghoshell.messenger import Input, Output


class Messenger(metaclass=ABCMeta):

    @abstractmethod
    def send(self, _input: Input) -> List[Output]:
        pass

    @abstractmethod
    def async_input(self, _input: Input) -> None:
        pass

    @abstractmethod
    def async_output(self, _output: Output) -> None:
        pass

    @abstractmethod
    async def await_async_input(self, handler: Callable[[Input], None]) -> None:
        pass

    @abstractmethod
    async def await_async_output(self, handler: Callable[[Output], None]) -> None:
        pass
