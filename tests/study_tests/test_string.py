def test_string_split_by_space() -> None:
    s = "/hello        world"
    val = [i for i in filter(lambda i: i, s.split(' '))]
    assert len(val) == 2


def test_strip_multi_chars() -> None:
    s = "```abc```"
    s = s.strip("`")
    assert s == "abc"
