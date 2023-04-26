from abc import ABCMeta
from typing import Optional, Dict


def test_late_static_bound() -> None:
    class Parent(metaclass=ABCMeta):

        def foo(self) -> "Parent":
            return self

        def bar(self) -> str:
            return "bar"

    class Child(Parent):

        def zoo(self) -> str:
            return "zoo"

    c = Child()
    assert isinstance(c.foo(), Child)
    assert c.bar() == "bar"
    assert c.zoo() == "zoo"


def test_optional_arg():
    # 必须设置默认值为 None, 否则 Optional 仍然会要求传参.
    def fn(a: Optional[str] = None) -> Optional[str]:
        return a

    assert fn() is None


def test_isinstance_typehint():
    a = {"a": "b"}
    assert isinstance(a, Dict)
