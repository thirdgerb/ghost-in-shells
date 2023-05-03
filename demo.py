#!/usr/bin/env python
import os.path

from ghoshell.container import Container
from ghoshell.ghost_fmk import GhostConfig
from ghoshell.mocks import MockGhost, MockMessageQueueProvider
from ghoshell.shell_protos import ConsoleShell


def main():
    config = GhostConfig(
        root_url=dict(
            resolver="test"
        )
    )
    container = Container()
    container.set(GhostConfig, config)
    container.register(MockMessageQueueProvider())

    pwd = os.getcwd()
    app_root = pwd + "/demo"
    ghost = MockGhost(container, app_root)
    ghost.boostrap()
    shell = ConsoleShell(ghost.container)
    shell.run_as_app()


if __name__ == "__main__":
    main()
