from abc import ABCMeta, abstractmethod
from typing import Optional, Dict

from ghoshell.ghost import IRuntime, Process


class IRuntimeDriver(metaclass=ABCMeta):

    @abstractmethod
    def get_process(self, process_id: str) -> Optional[Dict]:
        pass


class Runtime(IRuntime):
    _process: Process = None

    def __init__(self, driver: IRuntimeDriver, process_id: str):
        self._process_id: str = process_id
        self._driver: IRuntimeDriver = driver

    def process(self) -> Process:
        if self._process is None:
            process_data = self._driver.get_process(self._process_id)
            self._process = self._new_process(process_data)
        return self._process

    def process_gc(self) -> None:
        pass

    def _new_process(self, exists_process_data: Optional[Dict]) -> Process:
        pass

    def destroy(self) -> None:
        del self._process
        del self._driver
