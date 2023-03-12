from typing import List

from ghoshell.ghost import Input, Message


def test_basic_text():
    example = {
        "message": {
            "text": "hello world!",
        },
    }

    _input = Input(**example)
    assert _input.message.text == "hello world!"


def test_extend_input():
    """
    证明可以使用协议扩展来处理.
    """

    class TestInput(Input):
        class Msg(Message):
            images: List[str] = []

        message: Msg

    example = {
        "message": {
            "text": "hello world!",
            "images": ["image_url"]
        },
    }

    _input = TestInput(**example)
    assert _input.message.images[0] == "image_url"
    assert _input.dict().get("message", {}).get("images")[0] == "image_url"