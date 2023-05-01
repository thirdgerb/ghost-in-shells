import logging
from logging import getLogger
from logging.config import dictConfig

import yaml

from ghoshell.ghost import Ghost
from ghoshell.ghost_fmk.ghost import Bootstrapper


class FileLoggerBootstrapper(Bootstrapper):

    def __init__(
            self,
            logger_name: str = "ghoshell",
            file_name: str = "configs/logging.yaml",
    ):
        self.logger_name = logger_name
        self.file_name = file_name

    def bootstrap(self, ghost: Ghost):
        app_path = ghost.app_path()
        config_path = f"{app_path.rstrip('/')}/{self.file_name}"
        with open(config_path, "r", encoding="utf-8") as f:
            logging_config = yaml.safe_load(f)
            dictConfig(logging_config)

        # set logger
        logger = getLogger(self.logger_name)
        container = ghost.container
        container.set(logging.Logger, logger)
