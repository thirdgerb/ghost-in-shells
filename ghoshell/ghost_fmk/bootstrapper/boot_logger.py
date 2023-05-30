import logging
from logging import getLogger

from ghoshell.ghost import Ghost
from ghoshell.ghost_fmk.ghost import Bootstrapper


class FileLoggerBootstrapper(Bootstrapper):

    def __init__(
            self,
            logger_name: str = "ghoshell",
    ):
        self.logger_name = logger_name

    def bootstrap(self, ghost: Ghost):
        # set logger
        logger = getLogger(self.logger_name)
        container = ghost.container
        container.set(logging.Logger, logger)
