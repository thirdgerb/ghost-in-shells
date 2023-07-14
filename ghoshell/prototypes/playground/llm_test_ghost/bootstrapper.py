import os

import yaml

from ghoshell.framework.ghost import GhostBootstrapper
from ghoshell.ghost import Ghost
from ghoshell.prototypes.playground.llm_test_ghost.conversational import ConversationalThinkConfig, ConversationalThink
from ghoshell.prototypes.playground.llm_test_ghost.prompt_unittest import PromptUnitTestThinkDriver
from ghoshell.prototypes.playground.llm_test_ghost.undercover import UndercoverGameDriver


class LLMConversationalThinkBootstrapper(GhostBootstrapper):
    """
    实现一个最简单的 LLMs 单任务多轮对话的注册机.
    直接注册实例.
    todo: 需要实现从路径读取 json 或者 yaml 配置的办法.
    """

    def __init__(self, relative_path: str = "/conversational"):
        """
        用 dict 来传参可能范用性好一些.
        实际数据格式参考: ConversationalThinkConfig
        """
        self.relative_path = relative_path

    def bootstrap(self, ghost: Ghost):
        mindset = ghost.mindset
        config_path = ghost.config_path.rstrip("/") + "/" + self.relative_path.lstrip("/")
        for root, ds, fs in os.walk(config_path):
            for filename in fs:
                file_path = config_path.rstrip("/") + "/" + filename
                with open(file_path) as f:
                    config_data = yaml.safe_load(f)
                config = ConversationalThinkConfig(**config_data)
                think = ConversationalThink(config)
                mindset.register_think(think)


class PromptUnitTestsBootstrapper(GhostBootstrapper):

    def __init__(self, relative_config_path: str = "/llms/unittests", think_prefix: str = "unittests"):
        self.relative_config_path = relative_config_path
        self.think_prefix = think_prefix

    def bootstrap(self, ghost: Ghost):
        mindset = ghost.mindset
        root_dir = ghost.config_path.rstrip("/") + "/" + self.relative_config_path.strip("/")
        driver = PromptUnitTestThinkDriver(root_dir, think_prefix=self.think_prefix)
        mindset.register_driver(driver)
        for meta in driver.foreach_think():
            mindset.register_meta(meta)


class GameUndercoverBootstrapper(GhostBootstrapper):

    def __init__(self, relative_review_dir: str = "/games/undercover", think_name: str = None):
        self.relative_review_path = relative_review_dir
        self.think_name = think_name

    def bootstrap(self, ghost: Ghost):
        review_dir = ghost.runtime_path.rstrip("/") + "/" + self.relative_review_path.strip("/")
        driver = UndercoverGameDriver(
            review_dir,
            self.think_name,
        )
        mindset = ghost.mindset
        mindset.register_driver(driver)
        mindset.register_meta(driver.to_meta())
