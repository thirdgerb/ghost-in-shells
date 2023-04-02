from abc import ABCMeta, abstractmethod
from typing import Optional, Dict

from ghoshell.ghost import Runtime, Process, Task, TaskData
from ghoshell.ghost import UML


class IRuntimeDriver(metaclass=ABCMeta):

    @abstractmethod
    def get_process(self, process_id: str) -> Optional[Dict]:
        pass

    def lock_process(self, process_id: str) -> bool:
        pass

    def fetch_task_data(self, tid: str, is_long_term: bool) -> Optional[Dict]:
        pass

    def store_task_data(self, tid: str, data: TaskData) -> None:
        pass


class IRuntime(Runtime):

    def __init__(self, driver: IRuntimeDriver, session_id: str, root: UML, process_id: str):
        self._session_id: str = session_id
        self._process_id: str = process_id
        self._root_uml: UML = root
        self._driver: IRuntimeDriver = driver
        self._storing_task_data: Dict[str, TaskData] = {}
        self._processes: Dict[str, Process] = {}

    def current_process(self) -> Process:
        if self._process_id not in self._processes:
            process_data = self._driver.get_process(self._process_id)
            self._processes[self._process_id] = Process.parse_obj(process_data)
        return self._processes.get(self._process_id)

    def process_gc(self) -> None:
        pass

    def _new_process(self, exists_process_data: Optional[Dict]) -> Process:
        pass

    def lock_process(self, process_id: Optional[str]) -> bool:
        pass

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def current_process_id(self) -> str:
        return self._process_id

    def fetch_task(self, tid) -> Optional[Task]:
        ptr = self.current_process().tasks.get(tid)
        if ptr is None:
            return None
        data = self._driver.fetch_task_data(tid, ptr.is_long_term)
        return Task(ptr=ptr, data=data)

    def store_task(self, *tasks: Task) -> None:
        process = self.current_process()
        for task in tasks:
            # 临时保存，等待收尾阶段处理.
            process.store_task_ptr(task.ptr)
            self._storing_task_data[task.ptr.tid] = task.data

    def store_task_ptrs(self, *task_pointers: Task) -> None:
        pass

    def store_process(self, process: Process) -> None:
        pass

    def rewind(self) -> None:
        pass

    def quit_process(self) -> None:
        pass

    def destroy(self) -> None:
        del self._process
        del self._driver
