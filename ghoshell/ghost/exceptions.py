import sys
import traceback


class GhostException(Exception):
    """
    ghoshell 为 ghost 定义的 exception
    参考 http statuscode, 区分了几档.
    200~299: 正常区间
    300~399: 与 shell / client 通信的状态码.
    400~499: 表示客户端输入异常
    500~599: 表示系统自身异常, 通常会导致系统重启, 重置状态.

    todo: 注意, 现在还没研究过错误码, 都是乱写的.
    """

    CODE: int = 500

    def __init__(self, message: str, at: str = "", e: Exception = None):
        self.message: str = message
        self.at = at
        self.stack_info = ""
        if e is not None:
            stack_info = "\n".join(traceback.format_exception(e))
            self.stack_info = stack_info
        super().__init__(message)

    @classmethod
    def get_stack_info(cls) -> str:
        return "\n".join(traceback.format_exception(*sys.exc_info(), limit=3))


class StackoverflowException(GhostException):
    """
    出现了死循环逻辑, 用爆栈错误来中断.
    """
    CODE: int = 505


class UnhandledException(GhostException):
    """
    表示无法处理的消息.
    """
    CODE: int = 204
    pass


class MindsetNotFoundException(GhostException):
    """
    表示来到了没有思维存在的荒漠.
    """
    CODE: int = 404


class RuntimeException(GhostException):
    """
    致命错误, 系统应该重置所有的思维.
    """
    CODE: int = 505


class BusyException(GhostException):
    """
    系统忙碌.
    """
    CODE: int = 409


class ErrMessageException(GhostException):
    """
    用来传递信息的 err
    """
    CODE: int = 403


class OperatorException(GhostException):
    CODE: int = 522


class BootstrapException(GhostException):
    CODE: int = 600
