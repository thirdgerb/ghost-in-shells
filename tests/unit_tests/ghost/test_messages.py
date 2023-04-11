from ghoshell.ghost import Input


def test_basic_text():
    example = {
        "payload": {
            "text": {
                "raw": "hello world!",
            }
        },
    }

    _input = Input(**example)
    assert _input.payload.text.raw == "hello world!"
