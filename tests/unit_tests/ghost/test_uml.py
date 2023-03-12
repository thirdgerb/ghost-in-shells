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
            "state": "",
            "args": {"e": 123}
        },
        Test().dict(),
    ]

    for case in cases:
        uml = UML(**case)
        assert uml.dict() == case
        print(uml.dict())
