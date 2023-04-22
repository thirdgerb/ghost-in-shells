from ghoshell.ghost import URL


def test_ghost_url():
    class Test(URL):
        resolver: str = "e/f/g"
        args: str = {
            "h": 123
        }

    cases = [
        {
            "think": "a/b/c",
            "stage": "",
            "args": {"e": 123}
        },
        Test().dict(exclude_none=True),
    ]

    for case in cases:
        url = URL(**case)
        assert url.dict(exclude_none=True) == case
