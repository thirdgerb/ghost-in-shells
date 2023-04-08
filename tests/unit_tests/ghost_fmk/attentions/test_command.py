from ghoshell.ghost_fmk.attentions.command import CommandLine, CommandDriver


def test_driver_baseline() -> None:
    driver = CommandDriver('/')

    command = CommandLine(uml={"think": "/hello"}, config={
        "name": "foo",
        "description": "foo is a command name",
        "epilog": "end info",
        "argument": {
            "name": "first",
        },
        "options": [
            {
                "name": "option",
                "short": "o",
                "nargs": "?",
                "default": "option",
            },
            {
                "name": "second",
                "short": "s",
                "nargs": "?",
                "default": None,
            }
        ]
    })

    matched = driver.match_raw_text("/foo -h", command)
    assert matched is not None
    assert matched.result is not None
    assert matched.result.error is False

    matched = driver.match_raw_text("/foo foo -o ", command)
    assert matched is not None
    assert matched.result is not None
    assert matched.result.error is False
    assert matched.result.params == {"first": "foo", "second": None, "option": "option"}
