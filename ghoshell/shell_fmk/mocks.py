import asyncio

from ghoshell.messages import Output, Input
from ghoshell.shell_fmk.messengers import MessageQueue


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
