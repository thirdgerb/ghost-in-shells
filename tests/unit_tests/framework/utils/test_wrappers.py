from ghost.utils import dict2object


def test_dict2object() -> None:
    class Stub:
        class Sub:
            bar = 123
            zoo = ""

        foo = "hello"
        sub = Sub()

    s = Stub
    s = dict2object({"foo": "world", "bar": "k", 1: "world", "sub": {"bar": 456}}, s)
    assert s.sub.zoo == ""
    assert s.sub.bar == 456
    assert s.foo == "world"
    assert not hasattr(s, "bar")
