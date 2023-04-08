def test_string_split_by_space() -> None:
    s = "/hello        world"
    val = [i for i in filter(lambda i: i, s.split(' '))]
    assert len(val) == 2
