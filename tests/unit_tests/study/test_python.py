def test_multi_args():
    def list_of_str(*args: str) -> int:
        return len(args)

    assert 3 == list_of_str("a", "b", "c")
    assert 0 == list_of_str()
    assert list_of_str() is not None


def test_split_array():
    e = ["a"]
    b = e[1:]
    assert len(b) == 0
