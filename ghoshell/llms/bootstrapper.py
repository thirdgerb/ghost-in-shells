import os
from typing import List, Dict

import yaml

from ghoshell.ghost import Ghost
from ghoshell.ghost_fmk import Bootstrapper
from ghoshell.llms.thinks.conversational import ConversationalThinkConfig, ConversationalThink
from ghoshell.llms.thinks.llm_unit_test import LLMUnitTestThinkConfig, LLMUnitTestThink


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


class LLMUnitTestsThinkBootstrapper(Bootstrapper):

    def __init__(self, config_path: str = "/configs/llms/unittests", think_prefix: str = "unittest"):
        self.config_path = config_path
        self.think_prefix = think_prefix

    def bootstrap(self, ghost: Ghost):
        dir_name = "/".join([ghost.app_path().rstrip("/"), self.config_path.lstrip("/")])
        mindset = ghost.mindset
        for root, ds, fs in os.walk(dir_name):
            for filename in fs:
                if not filename.endswith(".yaml"):
                    continue
                fullname = dir_name + "/" + filename
                with open(fullname) as f:
                    data = yaml.safe_load(f)
                    if "think_name" not in data:
                        name = f"unittests/{filename}"
                        name = name[:len(name) - len(".yaml")]
                        data["think_name"] = name
                    config = LLMUnitTestThinkConfig(**data)
                    think = LLMUnitTestThink(config)
                    mindset.register_think(think)
