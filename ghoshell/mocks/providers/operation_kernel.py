from __future__ import annotations

from logging import Logger
from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.framework.ghost.operators import ReceiveInputOperator
from ghoshell.mocks.ghost_mock.bootstrappers import *


class OperatorMock(OperationKernel):

    def __init__(self, max_operators=10):
        self.max_operators = max_operators

    def record(self, ctx: Context, op: Operator) -> None:
        logger = ctx.container.force_fetch(Logger)
        logger.debug(f"run operator: {op}")
        return

    def save_records(self) -> None:
        return

    def is_stackoverflow(self, op: Operator, length: int) -> bool:
        return length > self.max_operators

    def init_operator(self) -> "Operator":
        return ReceiveInputOperator()

    def destroy(self) -> None:
        pass


class MockOperationKernelProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return OperationKernel

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return OperatorMock()
