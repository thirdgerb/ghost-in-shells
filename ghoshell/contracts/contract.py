from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, Any


class Container:
    def __init__(self):
        self.__instances: Dict[str, Any] = {}

    def set(self, abstract_name: str, instance: Any) -> None:
        self.__instances[abstract_name] = instance

    def get(self, abstract_name: str) -> Any | None:
        return self.__instances.get(abstract_name, None)


class Contract(metaclass=ABCMeta):

    @classmethod
    def fetch(cls, container: Container) -> Contract:
        abstract = cls.contract()
        name = abstract.__name__
        ins = container.get(name)
        if ins is None:
            raise ImportError(f"instance of {name} not found in contracts.Container")
        return ins

    @classmethod
    @abstractmethod
    def contract(cls) -> Type[Contract]:
        pass

    def register(self, container: Container) -> None:
        abstract = self.contract()
        container.set(abstract.__name__, self)
