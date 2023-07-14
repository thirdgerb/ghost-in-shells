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
        Test().model_dump(exclude_none=True),
    ]

    for case in cases:
        url = URL(**case)
        assert url.model_dump(exclude_none=True) == case
