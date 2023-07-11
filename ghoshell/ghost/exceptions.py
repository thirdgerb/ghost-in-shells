import sys
import traceback


class GhostException(Exception):
    """
    ghoshell 为 ghost 定义的 exception
    work in progress
    """

    CODE: int = 100

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


class ConversationException(GhostException):
    """
    会话过程中发生的异常.
    """

    CODE: int = 400


class ForbiddenException(ConversationException):
    CODE: int = 403


class UnhandledException(GhostException):
    """
    表示无法处理的消息.
    """
    CODE: int = 410
    pass


class BusyException(ConversationException):
    """
    系统忙碌.
    """
    CODE: int = 420


class ErrMessageException(ConversationException):
    """
    用来传递信息的 err
    """
    CODE: int = 430


class RuntimeException(GhostException):
    """
    无法响应的系统错误.
    由于会导致对话无法继续进行, 所以是致命错误, 系统应该重置所有的上下文.
    """
    CODE: int = 500


class MindsetNotFoundException(RuntimeException):
    """
    表示来到了没有思维存在的荒漠.
    通常是注册出了问题.
    """
    CODE: int = 510


class OperatorException(RuntimeException):
    """
    Runtime 的算子发生了错误.
    """
    CODE: int = 520


class StackoverflowException(GhostException):
    """
    出现了死循环逻辑, 用爆栈错误来中断.
    """
    CODE: int = 530


class LogicException(GhostException):
    """
    工程上的设计错误, 系统不应该启动.
    """
    CODE: int = 600


class BootstrapException(LogicException):
    CODE: int = 610
