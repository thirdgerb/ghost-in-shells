def test_multi_args() -> None:
    def list_of_str(*args: str) -> int:
        return len(args)

    assert 3 == list_of_str("a", "b", "c")
    assert 0 == list_of_str()
    assert list_of_str() is not None


def test_split_array() -> None:
    e = ["a"]
    b = e[1:]
    assert len(b) == 0


def test_union_argument() -> None:
    def test(a: str | None) -> str | None:
        return a

    assert test("a") == "a"
    assert test(None) is None


def test_del_dict_attr() -> None:
    a = {"a": 1, "b": 2}
    del a["a"]
    assert "a" not in a
