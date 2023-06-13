import logging
from logging import Logger, LoggerAdapter
from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.ghost import Context, BootstrapException


class ContextLoggerProvider(Provider):

    def __init__(self, logger_name: str = "ghoshell_context_logger"):
        self.logger_name = logger_name

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Logger

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        ctx = con.force_fetch(Context)
        if ctx.container.parent is None:
            raise BootstrapException("context container must be sub container of ghost")
        logger = logging.getLogger(self.logger_name)
        adapter = LoggerAdapter(logger, extra={"trace": ctx.input.trace.dict()})
        return adapter
