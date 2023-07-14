from abc import ABCMeta, abstractmethod
from typing import Dict, List

from ghoshell.ghost.runtime import Process
from ghoshell.messages import Tasked


class RuntimeDriver(metaclass=ABCMeta):

    @abstractmethod
    def get_current_process_id(self, session_id: str) -> str | None:
        pass

    @abstractmethod
    def set_current_process_id(self, session_id: str, process_id: str) -> None:
        pass

    @abstractmethod
    def get_process_data(self, session_id: str, process_id: str) -> Process | None:
        pass

    @abstractmethod
    def save_process_data(self, session_id: str, process_id: str, data: Process, overdue: int):
        pass

    @abstractmethod
    def get_task_data(self, session_id: str, process_id: str, task_id: str) -> Tasked | None:
        pass

    @abstractmethod
    def save_task_data(self, session_id: str, process_id: str, data: Dict[str, Tasked]):
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
