from logging import Logger
from typing import List

from ghoshell.container import Provider
from ghoshell.ghost_fmk.bootstrapper import FileLoggerBootstrapper, \
    CommandFocusDriverBootstrapper, LLMToolsFocusDriverBootstrapper
from ghoshell.ghost_fmk.ghost import GhostKernel
from ghoshell.ghost_fmk.operators import ReceiveInputOperator
from ghoshell.ghost_fmk.providers import ContextLoggerProvider
from ghoshell.llms import LLMTextCompletion, OpenAIChatCompletion
from ghoshell.llms.openai import OpenAIBootstrapper
from ghoshell.mocks.cache import MockCacheProvider
from ghoshell.mocks.ghost_mock.bootstrappers import *
from ghoshell.mocks.think_metas import ThinkMetaDriverMockProvider
from ghoshell.prototypes.conversational_ghost import ConversationalThinksBootstrapper
from ghoshell.prototypes.llm_test_ghost import GameUndercoverBootstrapper
from ghoshell.prototypes.llm_test_ghost import LLMConversationalThinkBootstrapper, PromptUnitTestsBootstrapper
from ghoshell.prototypes.sphero import SpheroGhostBootstrapper


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


class MockGhost(GhostKernel):
    # 启动流程. 想用这种方式解耦掉系统文件读取等逻辑.
    bootstrapper: List[Bootstrapper] = [
        FileLoggerBootstrapper(),
        RegisterThinkDemosBootstrapper(),
        CommandFocusDriverBootstrapper(),
        OpenAIBootstrapper(),

        ConversationalThinksBootstrapper(),
        LLMConversationalThinkBootstrapper(),
        LLMToolsFocusDriverBootstrapper(),
        # sphero 的逻辑驱动.
        SpheroGhostBootstrapper(),

        # 将 configs/llms/unitests 下的文件当成单元测试思维.
        PromptUnitTestsBootstrapper(),

        # 测试加入 undercover 游戏. deprecated
        GameUndercoverBootstrapper(think_name="game/undercover"),
    ]

    @classmethod
    def _depend_contracts(cls) -> List:
        contracts = super()._depend_contracts()
        appending = [LLMTextCompletion, OpenAIChatCompletion]
        for i in appending:
            contracts.append(i)
        return contracts

    @classmethod
    def _contracts_providers(cls) -> List[Provider]:
        return [
            MockCacheProvider(),
            ThinkMetaDriverMockProvider(),
            # LangChainTestLLMAdapterProvider(),
        ]

    @classmethod
    def _context_providers(cls) -> List[Provider]:
        return [
            ContextLoggerProvider(),
        ]

    def new_operation_kernel(self) -> "OperationKernel":
        return OperatorMock()
