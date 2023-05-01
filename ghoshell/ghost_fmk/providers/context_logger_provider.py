from logging import Logger, LoggerAdapter
from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.ghost import Context, BootstrapException


class ContextLoggerProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Logger

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        ctx = con.force_fetch(Context)
        if ctx.container.parent is None:
            raise BootstrapException("context container must be sub container of ghost")
        logger = ctx.container.parent.force_fetch(Logger)
        adapter = LoggerAdapter(logger, extra={"trace": ctx.input.trace.dict()})
        return adapter
