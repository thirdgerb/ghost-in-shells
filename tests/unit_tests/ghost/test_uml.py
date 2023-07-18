from ghoshell.url import URL


def test_ghost_url():
    class Test(URL):
        think: str = "e/f/g"
        args: dict = {
            "h": 123
        }

    cases = [
        {
            "think": "a/b/c",
            "stage": "",
            "args": {"e": 123}
        },
        Test().model_dump(),
    ]

    for case in cases:
        url = URL(**case)
        assert url.model_dump() == case
