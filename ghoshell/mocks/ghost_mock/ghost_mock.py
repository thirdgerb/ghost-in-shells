from typing import List

from ghoshell.container import Provider
from ghoshell.framework.bootstrapper import FileLoggerBootstrapper, \
    CommandFocusDriverBootstrapper, LLMToolsFocusDriverBootstrapper
from ghoshell.framework.ghost import GhostKernel
from ghoshell.llms import LLMTextCompletion, OpenAIChatCompletion
from ghoshell.llms.openai import OpenAIBootstrapper
from ghoshell.llms.thinks import ConversationalThinksBootstrapper, FileAgentMindsetBootstrapper
from ghoshell.mocks.ghost_mock.bootstrappers import *
from ghoshell.mocks.providers import *
from ghoshell.prototypes.playground.llm_test_ghost import GameUndercoverBootstrapper
from ghoshell.prototypes.playground.llm_test_ghost import LLMConversationalThinkBootstrapper, \
    PromptUnitTestsBootstrapper
from ghoshell.prototypes.playground.sphero import SpheroGhostBootstrapper


class MockGhost(GhostKernel):
    # 启动流程. 想用这种方式解耦掉系统文件读取等逻辑.

    def get_bootstrapper(self) -> List[GhostBootstrapper]:
        return [
            FileLoggerBootstrapper(),
            RegisterThinkDemosBootstrapper(),
            CommandFocusDriverBootstrapper(),
            OpenAIBootstrapper(),

            # 使用 llm chat completion 实现的思维
            ConversationalThinksBootstrapper(),
            # 使用 llm chat completion + function call 实现的思维.
            FileAgentMindsetBootstrapper(),

            LLMConversationalThinkBootstrapper(),
            LLMToolsFocusDriverBootstrapper(),
            # sphero 的逻辑驱动.
            SpheroGhostBootstrapper(),

            # 将 configs/llms/unitests 下的文件当成单元测试思维.
            PromptUnitTestsBootstrapper(),

            # 测试加入 undercover 游戏. deprecated
            GameUndercoverBootstrapper(think_name="game/undercover"),
        ]

    def get_depending_contracts(self) -> List:
        contracts = super().get_depending_contracts()
        appending = [LLMTextCompletion, OpenAIChatCompletion]
        for i in appending:
            contracts.append(i)
        return contracts

    def get_contracts_providers(self) -> List[Provider]:
        return [
            MockCacheProvider(),
            MockAPIRepositoryProvider(),
            MockMessageQueueProvider(),
            MockOperationKernelProvider(),
            MockThinkMetaDriverProvider(),
            # LocalThinkMetaStorageProvider(),
        ]
