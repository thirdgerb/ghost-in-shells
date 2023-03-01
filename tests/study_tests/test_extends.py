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
