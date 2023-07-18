from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict

from ghoshell.container import Container, Provider, Contract


def test_container_baseline():
    class Abstract(metaclass=ABCMeta):
        @abstractmethod
        def foo(self) -> int:
            pass

    class Foo(Abstract):
        count = 0

        def foo(self) -> int:
            self.count += 1
            return self.count

    #
    # class TestProvider(Provider):
    #     contract = Abstract
    #
    #     @classmethod
    #     def factory(cls, c: Container) -> Abstract | None:
    #         return Foo()

    class FooProvider(Provider):

        def __init__(self, singleton: bool):
            self._s = singleton

        def singleton(self) -> bool:
            return self._s

        def contract(self) -> Type[Abstract]:
            return Abstract

        def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
            return Foo()

    # 初始化
    container = Container()
    container.set(Abstract, Foo())

    # 获取单例
    foo = container.fetch(Abstract)
    assert foo.foo() == 1
    foo = container.fetch(Abstract)
    assert foo.foo() == 2  # 获取的是单例
    foo = container.fetch(Abstract)
    assert foo.foo() == 3

    # 注册 provider, 销毁了单例.
    container.register(FooProvider(True))

    # 二次取值. 替换了 原始实例, 但还是生成单例.
    foo = container.force_fetch(Abstract)
    assert foo.foo() == 1
    foo = container.force_fetch(Abstract)
    assert foo.foo() == 2

    # 注册 provider, 销毁了单例. 注册的是非单例
    container.register(FooProvider(False))
    foo = container.force_fetch(Abstract)
    assert foo.foo() == 1
    # 每次都是返回新实例.
    foo = container.force_fetch(Abstract)
    assert foo.foo() == 1
    assert foo.foo() == 2
