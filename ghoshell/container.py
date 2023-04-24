from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, Any, TypeVar

Contract = TypeVar('Contract', bound=object)


class Container:
    """
    一个简单的容器, 用来存放一些有隔离级别的单例.

    Python 没有比较方便的 IOC, 用来解耦各种与架构设计无关的 interface 获取.
    所以自己做了一个极简的方式, 方便各种工具封装成 Provider, 在工程里解耦使用.
    """

    def __init__(self, parent: Container | None = None):
        self.__instances: Dict[Type[Contract], Contract] = {}
        self.__parent = parent
        self.__providers: Dict[Type[Contract], Provider] = {}

    def set(self, contract: Type[Contract], instance: Contract) -> Any:
        """
        设置一个实例, 不会污染父容器.
        """
        self.__instances[contract] = instance

    def get(self, contract: Type[Contract]) -> Contract | None:
        """
        获取一个实例.
        """
        got = self.__instances.get(contract, None)
        if got is not None:
            return got

        #  第二高优先级.
        if contract in self.__providers:
            provider = self.__providers[contract]
            made = provider.factory(self)
            if made is not None and provider.singleton():
                self.set(contract, made)
            return made

        # 第三优先级.
        if self.__parent is not None:
            return self.__parent.get(contract)
        return None

    def register(self, provider: Provider) -> None:
        contract = provider.contract()
        del self.__instances[contract]
        self.__providers[contract] = provider

    def destroy(self) -> None:
        del self.__instances
        del self.__parent
        del self.__providers


class Provider(metaclass=ABCMeta):

    @abstractmethod
    def singleton(self) -> bool:
        pass

    @abstractmethod
    def contract(self) -> Type[Contract]:
        pass

    @abstractmethod
    def factory(self, con: Container) -> Contract | None:
        pass


def fetch(con: Container, contract: Type[Contract]) -> Contract | None:
    instance = con.get(contract)
    if instance is not None and isinstance(instance, contract):
        return instance
    return None


def force_fetch(con: Container, contract: Type[Contract]) -> Contract:
    ins = fetch(con, contract)
    if ins is None:
        raise Exception("todo")
    return ins
