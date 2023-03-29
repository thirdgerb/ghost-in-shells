from abc import ABCMeta, abstractmethod
from typing import Optional, Dict

from ghoshell.ghost import Runtime, Process
from ghoshell.ghost import UML


class IRuntimeDriver(metaclass=ABCMeta):

    @abstractmethod
    def get_process(self, process_id: str) -> Optional[Dict]:
        pass


class IRuntime(Runtime):
    _process: Process = None

    def __init__(self, driver: IRuntimeDriver, session_id: str, root: UML, process_id: str):
        self._session_id: str = session_id
        self._process_id: str = process_id
        self._root_uml: UML = root
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
