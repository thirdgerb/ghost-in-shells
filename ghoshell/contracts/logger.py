import logging
from typing import Type

from ghoshell.contracts.contract import Contract


class LogManager(Contract):
    """
    日志的容器.
    """

    def __init__(self, name: str | None):
        self.name = name if name else LogManager.__name__
        self.logger = logging.getLogger(name)

    def new_adapter(self, extra) -> logging.LoggerAdapter:
        return logging.LoggerAdapter(self.logger, extra=extra)

    @classmethod
    def contract(cls) -> Type[Contract]:
        return LogManager
