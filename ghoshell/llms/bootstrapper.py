from typing import List, Dict

from ghoshell.ghost import Ghost
from ghoshell.ghost_fmk import Bootstrapper
from ghoshell.llms.thinks.conversational import ConversationalThinkConfig, ConversationalThink


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
