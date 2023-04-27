from abc import ABCMeta, abstractmethod

from ghoshell.messages import Output, Input


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
