class GhostException(Exception):
    CODE: int = 500

    def __init__(self, message):
        self.message: str = message
        super(GhostException).__init__(message)


class StackoverflowException(GhostException):
    CODE: int = 505


class MissUnderstoodException(GhostException):
    pass


class MindsetNotFoundException(GhostException):
    CODE: int = 404


class RuntimeException(GhostException):
    CODE: int = 503


class BusyException(GhostException):
    CODE: int = 409
