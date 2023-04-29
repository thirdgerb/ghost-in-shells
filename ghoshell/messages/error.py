import sys
import traceback

from ghoshell.messages.base import Message


class Error(Message):
    KIND = "error"

    errcode: int = 500
    errmsg: str = ""
    at: str = ""
    stack_info: str = ""

    @classmethod
    def wrap(cls, code: int, err: Exception, limit: int = 5) -> "Error":
        trace = "\n".join(traceback.format_exception(*sys.exc_info(), limit=limit))
        wrapped = Error(errcode=code, errmsg=f"{err}", stack_info=trace)
        return wrapped
