from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import ClassVar, Dict, Any

from ghoshell.ghost.context import Context


class Memo(metaclass=ABCMeta):
    KIND: ClassVar[str] = ""

    @abstractmethod
    def index(self) -> Any:
        pass

    @abstractmethod
    def dict(self) -> Dict:
        pass

    def fetch(self, ctx: Context) -> Memo | None:
        return ctx.clone.memory.recall(self.KIND, self.index())


class MemoryDriver(metaclass=ABCMeta):

    @abstractmethod
    def kind(self) -> str:
        pass

    @abstractmethod
    def recall(self, index: Any) -> Memo | None:
        pass

    @abstractmethod
    def save(self, memo: Memo) -> None:
        pass


class Memory(metaclass=ABCMeta):

    @abstractmethod
    def clone(self, clone_id: str) -> Memory:
        pass

    @abstractmethod
    def memorize(self, memo: Memo) -> None:
        pass

    @abstractmethod
    def recall(self, kind: str, index: Any) -> Memo | None:
        pass

    @abstractmethod
    def register(self, driver: MemoryDriver) -> None:
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
