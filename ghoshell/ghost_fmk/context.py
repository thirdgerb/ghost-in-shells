from typing import List, Dict, Any, Optional, Type

from ghoshell.ghost import *
from ghoshell.ghost.context import Sender, M
from ghoshell.ghost_fmk.mind import MindImpl
from ghoshell.ghost_fmk.sending import SendingImpl


class ContextImpl(Context):

    def __init__(
            self,
            inpt: Input,
            clone: Clone,
            session: Session,
            runtime: Runtime,
    ):
        self._clone = clone

        # 初始化 input
        self._origin_input = inpt
        # 防止交叉污染.
        self._input = Input(**inpt.dict())

        # 初始化其它参数.
        self._failed: bool = False
        self._cache: Dict[str, Any] = {}
        self._async_inputs_buffer: List[Input] = []
        self._minder: MindImpl | None = None
        self._session = session
        self._runtime = runtime
        self._outputs_buffer = []
        self._messenger: SendingImpl | None = None

    @property
    def clone(self) -> Clone:
        return self._clone

    def send_at(self, _with: Optional["Thought"]) -> Sender:
        if self._messenger is not None:
            self._messenger.destroy()
        tid = _with.tid if _with else self.runtime.current_process().awaiting
        self._messenger = SendingImpl(tid, self)
        return self._messenger

    @property
    def input(self) -> "Input":
        return self._input

    def set_input(self, _input: "Input") -> None:
        self._input = _input

    def mind(self, this: Optional["Thought"]) -> "Mind":
        if self._minder is not None:
            self._minder.destroy()
        if this is None:
            awaiting = RuntimeTool.fetch_awaiting_task(self)
            self._minder = MindImpl(awaiting.tid, awaiting.url.copy_with())
        else:
            self._minder = MindImpl(this.tid, this.url.copy_with())
        return self._minder

    def read(self, expect: Type[M]) -> M | None:
        return expect.from_payload(self.input.payload)

    def async_input(self, _input: Input) -> None:
        _input.is_async = True
        self._async_inputs_buffer.append(_input)
        return

    def output(self, _output: "Output") -> None:
        # 异步输入只能返回异步输出.
        if self._input.is_async:
            # 这一步应该有别的地方实现了.
            _output.is_async = True
        # 用一个数组 buffer
        self._outputs_buffer.append(_output)

    def get_outputs(self) -> List["Output"]:
        return self._outputs_buffer

    def get_async_inputs(self) -> List["Input"]:
        return self._async_inputs_buffer

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key, None)

    @property
    def runtime(self) -> "Runtime":
        return self._runtime

    @property
    def session(self) -> "Session":
        return self._session

    def finish(self, failed: bool = False) -> None:

        # destroy temporary instance
        if self._messenger is not None:
            self._messenger.destroy()
        if self._minder is not None:
            self._minder.destroy()

        # session saving
        # self.session.save_input(self._input)
        # for output in self._outputs_buffer:
        #     self.session.save_output(output)

        self._runtime.finish()

    def destroy(self) -> None:
        self._runtime.destroy()
        self._session.destroy()
        # del
        del self._clone
        del self._session
        del self._runtime
        del self._origin_input
        del self._input
        del self._outputs_buffer
        del self._async_inputs_buffer
        del self._failed
        del self._cache
        del self._messenger
        del self._minder
