from ghoshell.container import Container
from ghoshell.ghost import OperationKernel, Operator
from ghoshell.ghost_fmk.config import GhostConfig
from ghoshell.ghost_fmk.ghost import GhostKernel
from ghoshell.ghost_fmk.operators import ReceiveInputOperator


class OperatorMock(OperationKernel):

    def __init__(self, max_operators=10):
        self.max_operators = max_operators

    def record(self, op: Operator) -> None:
        return

    def save_records(self) -> None:
        return

    def is_stackoverflow(self, op: Operator, length: int) -> bool:
        return length > self.max_operators

    def init_operator(self) -> "Operator":
        return ReceiveInputOperator()

    def destroy(self) -> None:
        pass


class GhostMock(GhostKernel):
    def __init__(self):
        super().__init__(
            "mock_ghost",
            container=Container(),
            root_path="mock",
            config=GhostConfig(
                root_url=dict(
                    resolver="test"
                )
            )
        )

    def new_operation_kernel(self) -> "OperationKernel":
        return OperatorMock()
