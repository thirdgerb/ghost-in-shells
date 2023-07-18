class GhostError(RuntimeError):
    """
    ghoshell 为 ghost 定义的 exception
    work in progress
    """

    CODE: int = 100

    def __init__(self, message: str):
        self.message: str = message
        super().__init__(message)


class ContextError(GhostError):
    CODE: int = 400


class ForbiddenError(ContextError):
    CODE: int = 403


class UnexpectedError(ContextError):
    """
    表示无法处理的消息.
    """
    CODE: int = 410
    pass


class BusyError(ContextError):
    """
    系统忙碌.
    """
    CODE: int = 420


class ThinkError(ContextError):
    """
    用来传递信息的 err
    """
    CODE: int = 430


class CloneError(GhostError):
    """
    无法响应的系统错误.
    由于会导致对话无法继续进行, 所以是致命错误, 系统应该重置所有的上下文.
    """
    CODE: int = 500


class MindsetNotFoundError(CloneError):
    """
    表示来到了没有思维存在的荒漠.
    通常是注册出了问题.
    """
    CODE: int = 510


class OperatorError(CloneError):
    """
    Runtime 的算子发生了错误.
    """
    CODE: int = 520


class StackoverflowError(CloneError):
    """
    出现了死循环逻辑, 用爆栈错误来中断.
    """
    CODE: int = 530


class LogicError(GhostError):
    """
    工程上的设计错误, 系统不应该启动.
    """
    CODE: int = 600


class BootstrapError(LogicError):
    CODE: int = 610
