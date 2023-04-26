from abc import ABCMeta, abstractmethod
from typing import Optional, Iterator, Dict, List

from ghoshell.ghost.mindset import ThinkMeta
from ghoshell.messages import Tasked


class ThinkMetaDriver(metaclass=ABCMeta):

    @abstractmethod
    def fetch_local_meta(self, thinking: str, clone_id: str | None) -> Optional[ThinkMeta]:
        pass

    @abstractmethod
    def iterate_think_metas(self, clone_id: str | None) -> Iterator[ThinkMeta]:
        pass

    @abstractmethod
    def register_meta(self, meta: ThinkMeta, clone_id: str | None) -> None:
        pass


class RuntimeDriver(metaclass=ABCMeta):

    @abstractmethod
    def get_current_process_id(self, session_id: str) -> str | None:
        pass

    @abstractmethod
    def set_current_process_id(self, session_id: str, process_id: str) -> None:
        pass

    @abstractmethod
    def get_process_data(self, session_id: str, process_id: str) -> Dict | None:
        pass

    @abstractmethod
    def save_process_data(self, session_id: str, process_id: str, data: Dict, overdue: int):
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

# --- providers --- #

# class ThinkMetaDriverProvider(Provider, metaclass=ABCMeta):
#
#     def singleton(self) -> bool:
#         return True
#
#     def contract(self) -> Type[Contract]:
#         return ThinkMetaDriver
#
#     @abstractmethod
#     def factory(self, con: Container) -> ThinkMetaDriver | None:
#         pass
