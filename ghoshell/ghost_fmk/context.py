import logging
from typing import List, Dict, Any, Optional

from ghoshell.ghost import *
from ghoshell.ghost.context import Messenger


class IContext(Context):

    def __init__(
            self,
            inpt: Input,
            clone: Clone
    ):
        self._clone = clone
        self._origin_input = inpt
        self._input = Input(**inpt.dict())
        self._logger = self._prepare_log()
        self._outputs: List[Output] = []
        self._failed: bool = False
        self._cache: Dict[str, Any] = {}
        self._async_inputs: List[Input] = []

    def _prepare_log(self) -> logging.LoggerAdapter:
        container = self.clone.ghost.container
        log = container.LogManager.fetch(container)
        adapter = log.new_adapter(self._input.trace.dict())
        return adapter

    @property
    def clone(self) -> Clone:
        return self._clone

    def send(self, _with: "Thought") -> Messenger:
        # todo
        pass

    @property
    def input(self) -> "Input":
        return self._input

    def set_input(self, _input: "Input") -> None:
        self._input = _input

    def async_input(self, _input: "Input") -> None:
        _input.is_async = True
        self._async_inputs.append(_input)

    def output(self, _output: "Output") -> None:
        self._outputs.append(_output)

    def get_outputs(self) -> List["Output"]:
        return self._outputs

    def get_async_inputs(self) -> List["Input"]:
        return self._async_inputs

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key, None)

    def finish(self, failed: bool = False) -> None:
        self.clone.runtime.finish(failed)
        # clone 也需要回收.
        self.clone.finish()

        # del
        del self._clone
        del self._origin_input
        del self._input
        del self._logger
        del self._outputs
        del self._async_inputs
        del self._failed
        del self._cache
