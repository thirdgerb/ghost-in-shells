from typing import List, Dict, Any, Optional, Type

from ghoshell.container import Container
from ghoshell.contracts import Cache
from ghoshell.framework.contracts import RuntimeDriver
from ghoshell.framework.ghost.config import GhostConfig
from ghoshell.framework.ghost.mind import MindImpl
from ghoshell.framework.ghost.runtime import RuntimeImpl
from ghoshell.framework.ghost.sending import SendingImpl
from ghoshell.framework.ghost.session import SessionImpl
from ghoshell.ghost import *
from ghoshell.messages import *
from ghoshell.utils import InstanceCount


class ContextImpl(Context):

    def __init__(
            self,
            inpt: Input,
            clone: Clone,
            container: Container,
            config: GhostConfig,
            # session: Session,
            # runtime: Runtime,
    ):
        self._clone = clone
        self._container = container
        self._config = config

        self._session: Session | None = None
        self._runtime: Runtime | None = None

        # 初始化 input
        self._origin_input = inpt
        # 防止交叉污染.
        self._input = Input(**inpt.model_dump())

        # 初始化其它参数.
        self._failed: bool = False
        self._cache: Dict[str, Any] = {}
        self._async_inputs_buffer: List[Input] = []
        self._minder: MindImpl | None = None
        self._outputs_buffer = []
        self._messenger: SendingImpl | None = None
        self._failed: bool = False
        InstanceCount.add(self.__class__.__name__)

    @property
    def clone(self) -> Clone:
        return self._clone

    @property
    def container(self) -> "Container":
        return self._container

    def send_at(self, _with: Optional["Thought"]) -> Sender:
        if self._messenger is not None:
            self._messenger.destroy()
        tid = _with.tid if _with else self.runtime.current_process().current
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
            awaiting = RuntimeTool.fetch_current_task(self)
            self._minder = MindImpl(awaiting.tid, awaiting.url.copy_with())
        else:
            self._minder = MindImpl(this.tid, this.url.copy_with())
        return self._minder

    def read(self, expect: Type[Message]) -> Message | None:
        return expect.read(self.input.payload)

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
        if self._runtime is None:
            driver = self._container.force_fetch(RuntimeDriver)
            trace = self._input.trace

            def new_process_id() -> str:
                return self.session.new_process_id()

            runtime = RuntimeImpl(
                driver,
                self._config,
                self._clone.clone_id,
                trace.session_id,
                trace.process_id,
                new_process_id,
            )
            self._container.set(Runtime, runtime)
            self._runtime = runtime
        return self._runtime

    @property
    def session(self) -> "Session":
        if self._session is None:
            cache = self._container.force_fetch(Cache)
            trace = self._input.trace
            session = SessionImpl(
                cache,
                clone_id=self._clone.clone_id,
                session_id=trace.session_id,
                expire=self._config.session_overdue,
            )
            self._container.set(Session, session)
            self._session = session
        return self._session

    def fail(self):
        self._failed = True
        # 清空数据.
        self._input = self._origin_input.copy()
        self._async_inputs_buffer = []
        self._outputs_buffer = []

    def finish(self) -> None:
        if self._failed:
            return
        # destroy temporary instance
        if self._messenger is not None:
            self._messenger.destroy()
        if self._minder is not None:
            self._minder.destroy()

        # session saving
        # self.session.save_input(self._input)
        # for output in self._outputs_buffer:
        #     self.session.save_output(output)
        self.runtime.finish()

    def destroy(self) -> None:
        if self._runtime is not None:
            self._runtime.destroy()
        if self._session is not None:
            self._session.destroy()
        if self._container is not None:
            self._container.destroy()

        # del
        del self._clone
        del self._container
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

    def __del__(self):
        InstanceCount.rm(self.__class__.__name__)
