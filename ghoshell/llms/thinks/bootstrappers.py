import os
from typing import Iterator, Tuple

import yaml

from ghoshell.framework.ghost import GhostBootstrapper
from ghoshell.ghost import Ghost
from ghoshell.llms.thinks.agent import FileAgentMindset, FileAgentFuncStorage, AgentFuncStorage
from ghoshell.llms.thinks.conversational import ConversationalConfig, ConversationalThink


class ConversationalThinksBootstrapper(GhostBootstrapper):
    """
    支持注册多个
    """

    def __init__(self, relative_config_dir: str = "conversational_thinks"):
        self.relative_config_dir = relative_config_dir

    def bootstrap(self, ghost: Ghost):
        config_path = ghost.config_path.rstrip("/") + "/" + self.relative_config_dir.lstrip("/")
        mindset = ghost.mindset
        for value in self.iterate_think_filename(config_path):
            filename, fullname = value
            with open(filename) as f:
                config_data = yaml.safe_load(f)
            config = ConversationalConfig(**config_data)
            if not config.name:
                config.name = fullname
            think = ConversationalThink(config)
            mindset.register_think(think)

        # for root, ds, fs in os.walk(config_path):
        #     for filename in fs:
        #         file_path = config_path.rstrip("/") + "/" + filename
        #         with open(file_path) as f:
        #             config_data = yaml.safe_load(f)
        #         config = ConversationalConfig(**config_data)
        #         think = ConversationalThink(config)
        #         mindset.register_think(think)

    @classmethod
    def iterate_think_filename(cls, directory: str) -> Iterator[Tuple[str, str]]:
        for root, ds, fs in os.walk(directory):
            for filename in fs:
                if not filename.endswith(".yaml"):
                    continue
                name = filename[: len(filename) - 5]
                filename = root.rstrip("/") + "/" + filename
                namespace = root[len(directory):]
                fullname = namespace.rstrip("/") + "/" + name
                yield filename, fullname.lstrip("/")


class FileAgentFuncStorageBootstrapper(GhostBootstrapper):
    """
    基于本地文件提供全局可用的 agent func.
    """

    def __init__(self, relative_config_file="agent_funcs/agent_funcs.yaml"):
        self.relative_config_file = relative_config_file

    def bootstrap(self, ghost: Ghost):
        storage = FileAgentFuncStorage(ghost.config_path, self.relative_config_file)
        ghost.container.set(AgentFuncStorage, storage)


class FileAgentMindsetBootstrapper(GhostBootstrapper):
    """
    基于本地文件实现 agent 的配置.
    """

    def __init__(self, relative_config_dir="agent_thinks", prefix: str = "agents"):
        self.relative_config_dir = relative_config_dir
        self.think_prefix = prefix

    def bootstrap(self, ghost: Ghost):
        config_path = ghost.config_path.rstrip("/") + "/" + self.relative_config_dir.lstrip("/")
        mindset = FileAgentMindset(config_path, self.think_prefix)
        ghost.mindset.register_sub_mindset(mindset)
