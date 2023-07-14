import asyncio
from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.framework.shell.messengers import MessageQueue
from ghoshell.messages import Output, Input


class MockMessageQueue(MessageQueue):

    def __init__(self):
        self._inputs = []
        self._outputs = []

    def push_input(self, _input: Input) -> None:
        self._inputs.insert(0, _input)

    def push_output(self, _output: Output) -> None:
        self._outputs.insert(0, _output)

    async def pop_input(self) -> Input:
        while True:
            if len(self._inputs) > 0:
                return self._inputs.pop()
            await asyncio.sleep(1)

    async def pop_output(self) -> Output:
        while True:
            if len(self._outputs) > 0:
                return self._outputs.pop()
            await asyncio.sleep(1)

    def ack_output(self, output_id: str, success: bool) -> None:
        pass

    def ack_input(self, input_id: str, success: bool) -> None:
        pass


class MockMessageQueueProvider(Provider):
    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return MessageQueue

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return MockMessageQueue()
