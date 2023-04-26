from abc import ABCMeta, abstractmethod
from typing import Callable, Optional, List

from ghoshell.ghost import Ghost
from ghoshell.messages import Output, Input
from ghoshell.shell import Messenger


class MessageQueue(metaclass=ABCMeta):

    @abstractmethod
    def push_input(self, _input: Input) -> None:
        pass

    @abstractmethod
    def push_output(self, _output: Output) -> None:
        pass

    @abstractmethod
    async def pop_input(self) -> Input:
        pass

    @abstractmethod
    async def pop_output(self) -> Output:
        pass

    @abstractmethod
    def ack_output(self, output_id: str, success: bool) -> None:
        pass

    @abstractmethod
    def ack_input(self, input_id: str, success: bool) -> None:
        pass


class SyncGhostMessenger(Messenger):

    def __init__(self, ghost: Ghost, queue: MessageQueue):
        self._ghost = ghost
        self._queue = queue

    def send(self, _input: Input) -> Optional[List[Output]]:
        try:
            outputs = self._ghost.respond(_input)
            if outputs is None:
                return None
            result = []
            for _output in outputs:
                if _output.is_async:
                    self._queue.push_output(_output)
                else:
                    result.append(result)
            return result
        # todo catch exceptions
        finally:
            pass

    def send_async_input(self, _input: Input) -> None:
        _input.is_async = True
        self._queue.push_input(_input)

    async def await_async_output(self, handler: Callable[[Output], None]) -> None:
        _input = await self._queue.pop_input()
        outputs = self.send(_input)
        if outputs is None:
            # success
            self._queue.ack_input(_input.mid, False)
            return None
        for _output in outputs:
            handler(_output)


class AsyncShellMessenger(Messenger):

    def __init__(self, queue: MessageQueue):
        self._queue = queue

    def send(self, _input: Input) -> Optional[List[Output]]:
        return None

    def send_async_input(self, _input: Input) -> None:
        _input.is_async = True
        self._queue.push_input(_input)

    async def await_async_output(self, handler: Callable[[Output], None]) -> None:
        _output = await self._queue.pop_output()
        try:
            handler(_output)
            self._queue.ack_output(_output.mid, True)
            return None
        # todo: ack output
        finally:
            pass
