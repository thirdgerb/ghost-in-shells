from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, Iterator

from ghoshell.meta import Meta


class ThinkMetaStorage(metaclass=ABCMeta):

    @abstractmethod
    def clone(self, clone_id: str | None) -> ThinkMetaStorage:
        pass

    @abstractmethod
    def fetch_meta(self, think_name: str, clone_id: str | None) -> Optional[Meta]:
        pass

    @abstractmethod
    def iterate_think_metas(self) -> Iterator[Meta]:
        pass

    @abstractmethod
    def register_meta(self, meta: Meta, clone_id: str | None) -> None:
        pass
