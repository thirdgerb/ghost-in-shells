from abc import ABCMeta, abstractmethod
from typing import Type

from ghoshell.container import Container, Provider


class Cache(metaclass=ABCMeta):

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
    def expire(self, key: str, exp: int) -> bool:
        pass

    @abstractmethod
    def set_member(self, key: str, member: str, value: str) -> bool:
        pass

    @abstractmethod
    def get_member(self, key: str, member: str) -> str | None:
        pass

    def remove_member(self, key: str, *member: str) -> int:
        pass

    @abstractmethod
    def remove(self, *keys: str) -> int:
        pass


class AbsCacheProvider(Provider, metaclass=ABCMeta):
    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Cache]:
        return Cache

    @abstractmethod
    def factory(self, con: Container) -> Cache | None:
        pass
