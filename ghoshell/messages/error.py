from ghoshell.messages.base import Message


class ErrMsg(Message):
    KIND = "error"

    errcode: int = 500
    errmsg: str = ""
    stack_info: str = ""
