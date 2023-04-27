from typing import List

from ghoshell.container import Container, Provider
from ghoshell.ghost import OperationKernel, Operator
from ghoshell.ghost_fmk.config import GhostConfig
from ghoshell.ghost_fmk.ghost import GhostKernel, Bootstrapper
from ghoshell.ghost_fmk.operators import ReceiveInputOperator
from ghoshell.mocks.cache import MockCacheProvider
from ghoshell.mocks.ghost_mock.bootstrappers import RegisterThinkDemosBootstrapper
from ghoshell.mocks.think_metas import ThinkMetaDriverMockProvider


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


class MockGhost(GhostKernel):
    # 启动流程. 想用这种方式解耦掉系统文件读取等逻辑.
    bootstrapper: List[Bootstrapper] = [
        RegisterThinkDemosBootstrapper(),
    ]

    def __init__(self, container: Container, root_path: str):
        config = container.force_fetch(GhostConfig)
        super().__init__(
            "mock_ghost",
            container=container,
            root_path=root_path.rstrip("/"),
            config=config,
        )

    @classmethod
    def _contracts_providers(cls) -> List[Provider]:
        return [
            MockCacheProvider(),
            ThinkMetaDriverMockProvider(),
        ]

    @classmethod
    def _context_providers(cls) -> List[Provider]:
        return []

    def new_operation_kernel(self) -> "OperationKernel":
        return OperatorMock()
