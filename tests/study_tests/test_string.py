def test_string_split_by_space() -> None:
    s = "/hello        world"
    val = [i for i in filter(lambda i: i, s.split(' '))]
    assert len(val) == 2


def test_strip_multi_chars() -> None:
    s = "```abc```"
    s = s.strip("`")
    assert s == "abc"


def test_strip_yaml() -> None:
    text = """
好的，以下是您需要的指令：\n\n```\n- method: lambda_roll\n  speed: lambda t: 100\n\
 heading: lambda t: (120 if t < 2 else (240 if t < 4 else 0))\n  duration:\
6\n```\n\n这个指令会让我以 100 的速度向前滚动，滚动方向会在 0 到 120 度之间持续 2 秒，然后转到 120 到 240 度之间持续\
2 秒，最后回到 0 度持续 2 秒，这样就形成了一个三角形的形状。"
"""
    sections = text.split("```")
    assert len(sections) == 3


def test_multi_lines() -> None:
    a = "abc" \
        "efg"
    assert a == "abcefg"
