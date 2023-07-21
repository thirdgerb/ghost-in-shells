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


def test_function_doc():
    class Foo:

        def foo(self) -> None:
            """
            doc
            """
            return None

    f = Foo()
    foo = getattr(f, "foo")
    assert foo.__doc__.strip() == "doc"


def test_method_call():
    class Foo:
        def foo(self, bar: str) -> str:
            """
            doc
            """
            return bar

    f = Foo()
    # 不需要传入 self.
    foo = getattr(f, "foo")
    assert foo("bar") == "bar"


def test_func_doc():
    def foo():
        """
        bar
        """
        return "foo"

    assert foo.__doc__.strip() == "bar"


def test_super_from_abc_class():
    class Foo:
        @abc.abstractmethod
        def foo(self) -> str:
            return "foo"

    class Bar(Foo):
        def foo(self) -> str:
            return super().foo()

    b = Bar()
    assert b.foo() == "foo"


def test_method_decorator():
    def maker(zoo: str):
        def decorator(method):
            def caller(obj, bar: str):
                return method(obj, bar) + zoo

            return caller

        return decorator

    class Foo:

        @maker("zoo")
        def foo(self, bar: str) -> str:
            return bar

    f = Foo()
    assert f.foo("bar_") == "bar_zoo"


def test_is_instance():
    class Bar:
        bar: int = 1

    class Foo(Bar):
        foo: int = 2

    v = 1

    assert issubclass(Foo, Bar)
    assert not isinstance(1, type(object))
    assert isinstance(Foo, type(object))
