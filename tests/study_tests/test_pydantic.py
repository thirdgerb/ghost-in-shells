from typing import ClassVar
from typing import Dict

from pydantic import BaseModel, Field


def test_typing_dict() -> None:
    class Foo(BaseModel):
        bar: Dict = {}

    foo = Foo(bar={"a": "b"})
    assert foo.bar.get("a") == "b"

    class Zoo(Foo):
        class Bar(BaseModel):
            a: str

        bar: Bar

    zoo = Zoo(**foo.dict())
    assert zoo.bar.a == "b"

    zoo = Zoo.parse_obj(foo)
    assert zoo.bar.a == "b"

    # 判断默认值不会相互污染
    foo2 = Foo()
    assert len(foo2.bar) == 0
    assert len(foo.bar) == 1


def test_children_model_init() -> None:
    class Parent(BaseModel):
        class Child(BaseModel):
            foo: str
            bar: int

        child: Child

    # 可以通过字典给子实体赋值.
    p = Parent(child={"foo": "foo", "bar": 123})
    assert p.child.foo == "foo"
    assert p.child.bar == 123


def test_children_copy() -> None:
    class Parent(BaseModel):
        class Child(BaseModel):
            foo: str
            bar: int

        child: Child

    # 可以通过字典给子实体赋值.
    p = Parent(child={"foo": "foo", "bar": 123})

    copied = p.copy()
    copied.child.foo = "bar"
    assert copied.child.foo == "bar"
    # copy 不是深拷贝
    assert p.child.foo == "bar"

    copied = Parent(**p.dict())
    copied.child.foo = "foo"
    assert copied.child.foo == "foo"
    assert p.child.foo == "bar"


def test_class_var_constant() -> None:
    class Tester(BaseModel):
        foo: str
        BAR: ClassVar[str] = "bar"

    t = Tester(foo="foo")
    assert t.foo == "foo"
    assert t.BAR == "bar"
    assert t.dict().get("BAR") is None

    class Child(Tester):
        BAR = "zoo"

    c = Child(foo="foo")
    assert c.BAR == "zoo"
    assert c.dict().get("BAR") is None


def test_default_value_is_copy() -> None:
    class Parent(BaseModel):
        val: Dict = {}
        field: Dict = Field(default_factory=lambda: {})

    p = Parent()
    p.val["foo"] = "bar"
    p.field["foo"] = "bar"
    assert p.val.get("foo") == "bar"
    assert p.field.get("foo") == "bar"

    p2 = Parent()
    assert p2.val.get("foo") is None
    assert len(p2.field) == 0


def test_sub_model_default_value():
    class Foo(BaseModel):
        foo: str

        class Bar(BaseModel):
            zoo: str = "zoo"

        bar: Bar = Field(default_factory=Bar)

    foo = Foo(foo="foo")
    assert foo.bar.zoo == "zoo"


def test_new_with_sub_model():
    class Foo(BaseModel):
        foo: str

        class Bar(BaseModel):
            zoo: str = "zoo"

        bar: Bar

    foo = Foo(foo="foo", bar=dict(zoo="zoo"))
    assert foo.bar.zoo == "zoo"
