import logging
from logging import getLogger

from ghoshell.framework.ghost import GhostBootstrapper
from ghoshell.ghost import Ghost


class FileLoggerBootstrapper(GhostBootstrapper):

    def __init__(
            self,
            logger_name: str = "ghoshell",
    ):
        self.logger_name = logger_name

    def bootstrap(self, ghost: Ghost):
        # set logger
        logging.captureWarnings(True)
        logger = getLogger(self.logger_name)
        container = ghost.container
        container.set(logging.Logger, logger)
