from __future__ import annotations

import abc


def test_abstract_class_with_property() -> None:
    class Parent(metaclass=abc.ABCMeta):
        @property
        def prop(self):
            pass

    class Child(Parent):
        @property
        def prop(self):
            return "hello"

    c: Parent = Child()
    assert c.prop == "hello"


def test_use_property_as_param() -> None:
    class Parent(metaclass=abc.ABCMeta):
        prop: str

    class Child(Parent):
        abc = 123

        @property
        def prop(self):
            return "hello"

    c: Parent = Child()
    assert c.prop == "hello"


def test_return_self() -> None:
    class Foo:
        def bar(self) -> Foo:
            return self

    foo = Foo()
    assert foo is foo.bar()
    assert foo.bar() is foo.bar().bar()


def test_class_name() -> None:
    class Parent:
        @classmethod
        def name(cls) -> str:
            return cls.__name__

    class Child(Parent):
        pass

    c = Child()
    assert c.name() == Child.__name__
    assert c.name() != Parent.__name__
    assert Parent.__name__ != Child.__name__