from typing import Dict

from pydantic import BaseModel


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
