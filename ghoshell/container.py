from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, TypeVar

Contract = TypeVar('Contract', bound=object)


class Container:
    """
    一个简单的容器, 用来存放一些有隔离级别的单例.

    Python 没有比较方便的 IOC, 用来解耦各种与架构设计无关的 interface 获取.
    所以自己做了一个极简的方式, 方便各种工具封装成 Provider, 在工程里解耦使用.
    """

    def __init__(self, parent: Container | None = None):
        if parent is not None:
            if not isinstance(parent, Container):
                raise AttributeError("container can only initialized with parent Container")
            if parent is self:
                raise AttributeError("container's parent must not be itself")
        self.parent = parent
        self.__instances: Dict[Type[Contract], Contract] = {}
        self.__providers: Dict[Type[Contract], Provider] = {}

    def set(self, contract: Type[Contract], instance: Contract) -> None:
        """
        设置一个实例, 不会污染父容器.
        """
        self.__instances[contract] = instance

    def bound(self, contract: Type[Contract]) -> bool:
        return contract in self.__instances or contract in self.__providers or \
            (self.parent is not None and self.parent.bound(contract))

    def get(self, contract: Type[Contract], params: Dict | None = None) -> Contract | None:
        """
        获取一个实例.
        """
        got = self.__instances.get(contract, None)
        if got is not None:
            return got

        #  第二高优先级.
        if contract in self.__providers:
            provider = self.__providers[contract]
            made = provider.factory(self, params)
            if made is not None and provider.singleton():
                self.set(contract, made)
            return made

        # 第三优先级.
        if self.parent is not None:
            return self.parent.get(contract)
        return None

    def register(self, provider: Provider) -> None:
        contract = provider.contract()
        if contract in self.__instances:
            del self.__instances[contract]
        self.__providers[contract] = provider

    def fetch(self, contract: Type[Contract], strict: bool = False) -> Contract | None:
        instance = self.get(contract)
        if instance is not None:
            if strict and not isinstance(instance, contract):
                return None
            return instance
        return None

    def force_fetch(self, contract: Type[Contract], strict: bool = False) -> Contract:
        ins = self.fetch(contract, strict)
        if ins is None:
            raise Exception(f"contract {contract} not register in container")
        return ins

    def destroy(self) -> None:
        del self.__instances
        del self.parent
        del self.__providers


class Provider(metaclass=ABCMeta):

    @abstractmethod
    def singleton(self) -> bool:
        pass

    @abstractmethod
    def contract(self) -> Type[Contract]:
        pass

    @abstractmethod
    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        pass
