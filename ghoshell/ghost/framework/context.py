from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List

from ghoshell.ghost.context import Context
from ghoshell.ghost import Output, Attentions, Mindset, Input, Message
from ghoshell.ghost.runtime import Runtime

from ghoshell.ghost.framework import GhostKernel


class Context(Context):

    def __init__(
            self,
            ghost_id: str,
            inpt: Input,
            ghost: GhostKernel,
    ):
        self._ghost_id: str = ghost_id
        self._ghost: GhostKernel = ghost
        self._input: Input = inpt
        self._output_messages: List[Message] = []

    @property
    def name(self) -> str:
        return self._ghost.name

    @property
    def id(self) -> str:
        return self._ghost_id

    @property
    def input(self) -> Input:
        return self._input

    @property
    def mind(self) -> Mindset:
        pass

    @property
    def runtime(self) -> Runtime:
        pass

    @property
    def featuring(self) -> Featuring:
        pass

    @property
    def attentions(self) -> Attentions:
        pass

    def act(self, *messages: Message) -> None:
        tid = self.runtime.current_task().tid
        # 添加消息产生时的 tid
        for m in messages:
            m.tid = tid
        self._output_messages.append(*messages)

    def output(self) -> Output:
        return Output(
            input=self._input,
            messages=self._output_messages.copy(),
            env=self._ghost.ghost_env(self),
        )

    def destroy(self) -> None:
        del self._ghost
        del self._input
        del self._output_messages
