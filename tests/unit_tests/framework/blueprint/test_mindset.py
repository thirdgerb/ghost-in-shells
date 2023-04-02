from ghoshell.ghost.blueprint import This
from ghost.utils import dict2object


def test_this() -> None:
    class Foo(This):
        class Args:
            foo: str = ""

        class Data:
            bar: str = ""

        class Result:
            r: str = ""

        args: Args = Args()
        data: Data = Data()
        result: Result = None

    this = Foo()
    this = dict2object(
        {
            "args": {
                "foo": "hello"
            },
            "data": {
                "bar": "world"
            }
        },
        this,
    )
    assert this.args.foo == "hello"
    assert this.vars.bar == "world"
