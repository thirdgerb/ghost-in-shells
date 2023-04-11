from ghoshell.ghost import UML


def test_ghost_uml():
    class Test(UML):
        think: str = "e/f/g"
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
        uml = UML(**case)
        assert uml.dict(exclude_none=True) == case
