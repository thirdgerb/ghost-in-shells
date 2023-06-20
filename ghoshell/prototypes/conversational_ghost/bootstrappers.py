import os

import yaml

from ghoshell.ghost import Ghost
from ghoshell.ghost_fmk import Bootstrapper
from ghoshell.prototypes.conversational_ghost.conversational import ConversationalConfig, ConversationalThink


class ConversationalThinksBootstrapper(Bootstrapper):
    """
    支持注册多个
    """

    def __init__(self, relative_config_dir: str = "conversational_thinks"):
        self.relative_config_dir = relative_config_dir

    def bootstrap(self, ghost: Ghost):
        config_path = ghost.config_path.rstrip("/") + "/" + self.relative_config_dir.lstrip("/")
        mindset = ghost.mindset
        for root, ds, fs in os.walk(config_path):
            for filename in fs:
                file_path = config_path.rstrip("/") + "/" + filename
                with open(file_path) as f:
                    config_data = yaml.safe_load(f)
                config = ConversationalConfig(**config_data)
                think = ConversationalThink(config)
                mindset.register_think(think)
