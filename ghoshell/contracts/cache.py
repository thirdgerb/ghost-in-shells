from abc import ABCMeta, abstractmethod
from typing import Type

from ghoshell.container import Contract


class Cache(Contract, metaclass=ABCMeta):

    @classmethod
    def contract(cls) -> Type[Contract]:
        return Cache

    @abstractmethod
    def lock(self, key: str, overdue: int = 0) -> bool:
        pass

    @abstractmethod
    def unlock(self, key: str) -> bool:
        pass

    @abstractmethod
    def set(self, key: str, val: str, exp: int = 0) -> bool:
        pass

    @abstractmethod
    def get(self, key: str) -> str | None:
        pass

    @abstractmethod
    def remove(self, *keys: str) -> int:
        pass
