from abc import ABCMeta


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
