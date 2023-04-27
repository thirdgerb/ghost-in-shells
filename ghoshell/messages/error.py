from ghoshell.messages.base import Message


class Error(Message):
    KIND = "error"

    errcode: int = 500
    errmsg: str = ""
