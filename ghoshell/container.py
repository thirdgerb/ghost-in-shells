from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, Any


class Container:
    """
    一个简单的容器, 用来存放一些有隔离级别的单例.
    这个单例可以通过 contract 的方式来获取, 变更实现.
    Python 没有比较方便的 IOC, 用来解耦各种与架构设计无关的 interface 获取.
    所以自己做了一个极简的方式, 方便各种工具封装 Adapter, 在工程中复用
    """

    def __init__(self, parent: Container | None = None):
        self.__instances: Dict[str, Any] = {}
        self.__parent = parent

    def set(self, abstract_name: str, instance: Any) -> Any:
        """
        设置一个实例
        """
        self.__instances[abstract_name] = instance

    def get(self, abstract_name: str) -> Any | None:
        """
        获取一个实例.
        """
        got = self.__instances.get(abstract_name, None)
        if got is not None:
            return got
        if self.__parent is not None:
            return self.__parent.get(abstract_name)
        return None

    def destroy(self) -> None:
        del self.__instances
        del self.__parent


class Contract(metaclass=ABCMeta):

    @classmethod
    def fetch(cls, container: Container) -> Contract:
        abstract = cls.contract()
        name = abstract.__name__
        ins = container.get(name)
        if ins is None:
            raise ImportError(f"instance of {name} not found in contracts.Container")
        if not isinstance(ins, cls):
            # todo: 可以直接把 instance 当成 str 来输出吗?
            raise ImportError(f"instance of {ins} not implements contract {name}")
        return ins

    @classmethod
    @abstractmethod
    def contract(cls) -> Type[Contract]:
        """
        若干个 Contract 的实现, 可以有相同的 Contract 描述.
        回头研究一下泛型, 或许用泛型能够更方便实现.
        """
        pass

    def register(self, container: Container) -> None:
        """
        将自己注册成 Container 的实例.
        """
        abstract = self.contract()
        container.set(abstract.__name__, self)
