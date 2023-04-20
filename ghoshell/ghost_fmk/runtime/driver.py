import json
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from typing import Dict, List

from ghoshell.contracts import Cache

TaskData = namedtuple("TaskData", "data overdue")


class AbsRuntimeDriver(metaclass=ABCMeta):

    @abstractmethod
    def get_process_data(self, session_id: str, process_id: str) -> Dict | None:
        pass

    @abstractmethod
    def save_process_data(self, session_id: str, process_id: str, data: Dict, overdue: int):
        pass

    @abstractmethod
    def get_task_data(self, session_id: str, process_id: str, task_id: str) -> Dict | None:
        pass

    @abstractmethod
    def save_task_data(self, session_id: str, process_id: str, data: Dict[str, TaskData]):
        pass

    @abstractmethod
    def lock_process(self, session_id: str, process_id: str, overdue: int) -> bool:
        pass

    @abstractmethod
    def unlock_process(self, session_id: str, process_id: str) -> bool:
        pass

    @abstractmethod
    def remove_process(self, session_id: str, process_id: str) -> bool:
        pass

    @abstractmethod
    def remove_tasks(self, session_id: str, process_id: str, tasks: List[str]) -> int:
        pass


class CacheRuntimeDriver(AbsRuntimeDriver):

    def __init__(self, cache: Cache):
        self._cache = cache

    @staticmethod
    def _get_process_key(session_id: str, process_id: str):
        return f"runtime:process:{session_id}:{process_id}"

    @staticmethod
    def _get_task_key(tid: str):
        return f"runtime:task:{tid}"

    @staticmethod
    def _get_locker_key(session_id: str, process_id: str):
        return f"runtime:process:locker:{session_id}:{process_id}"

    def get_process_data(self, session_id: str, process_id: str) -> Dict | None:
        key = self._get_process_key(session_id, process_id)
        val = self._cache.get(key)
        if val is not None:
            return json.loads(val)
        return None

    def save_process_data(self, session_id: str, process_id: str, data: Dict, overdue: int):
        saving = json.dumps(data)
        key = self._get_process_key(session_id, process_id)
        overdue = overdue if overdue > 0 else 0
        self._cache.set(key, saving, overdue)

    def get_task_data(self, session_id: str, process_id: str, task_id: str) -> Dict | None:
        key = self._get_task_key(task_id)
        val = self._cache.get(key)
        if val is not None:
            return json.loads(val)
        return None

    def save_task_data(self, session_id: str, process_id: str, data: Dict[str, TaskData]):
        for tid in data:
            key = self._get_task_key(tid)
            task_data = data[tid]
            val = json.dumps(task_data.data)
            self._cache.set(key, val, task_data.overdue)

    def lock_process(self, session_id: str, process_id: str, overdue: int) -> bool:
        key = self._get_locker_key(session_id, process_id)
        return self._cache.lock(key, overdue)

    def unlock_process(self, session_id: str, process_id: str) -> bool:
        key = self._get_locker_key(session_id, process_id)
        return self._cache.unlock(key)

    def remove_process(self, session_id: str, process_id: str) -> bool:
        key = self._get_process_key(session_id, process_id)
        return self._cache.remove(key) == 1

    def remove_tasks(self, session_id: str, process_id: str, tasks: List[str]) -> int:
        keys = []
        for tid in tasks:
            key = self._get_task_key(tid)
            keys.append(key)
        return self._cache.remove(*keys)
