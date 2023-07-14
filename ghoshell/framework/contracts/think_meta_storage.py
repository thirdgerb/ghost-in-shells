from abc import ABCMeta, abstractmethod
from typing import Optional, Iterator

from ghoshell.ghost.mindset import ThinkMeta


class ThinkMetaStorage(metaclass=ABCMeta):

    @abstractmethod
    def fetch_meta(self, think_name: str, clone_id: str | None) -> Optional[ThinkMeta]:
        pass

    @abstractmethod
    def iterate_think_metas(self, clone_id: str | None) -> Iterator[ThinkMeta]:
        pass

    @abstractmethod
    def register_meta(self, meta: ThinkMeta, clone_id: str | None) -> None:
        pass
