from typing import List, Dict

from ghoshell.ghost import Ghost
from ghoshell.ghost_fmk import Bootstrapper
from ghoshell.llms.discover.conversational import ConversationalThinkConfig, ConversationalThink
from ghoshell.llms.discover.prompt_unittest import PromptUnitTestThinkDriver
from ghoshell.llms.discover.undercover import UndercoverGameDriver


class LLMConversationalThinkBootstrapper(Bootstrapper):
    """
    实现一个最简单的 LLMs 单任务多轮对话的注册机.
    直接注册实例.
    todo: 需要实现从路径读取 json 或者 yaml 配置的办法.
    """

    def __init__(self, configs: List[Dict]):
        """
        用 dict 来传参可能范用性好一些.
        实际数据格式参考: ConversationalThinkConfig
        """
        self.configs = configs

    def bootstrap(self, ghost: Ghost):
        mindset = ghost.mindset
        for config_data in self.configs:
            config = ConversationalThinkConfig(**config_data)
            think = ConversationalThink(config)
            mindset.register_think(think)


class PromptUnitTestsBootstrapper(Bootstrapper):

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


class GameUndercoverBootstrapper(Bootstrapper):

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
