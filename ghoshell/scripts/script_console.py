#!/usr/bin/env python
import argparse
import os.path
import sys
from logging.config import dictConfig

import yaml

from ghoshell.container import Container
from ghoshell.framework.ghost import GhostConfig
from ghoshell.ghost import Ghost
from ghoshell.mocks.ghost_mock import MockGhost
from ghoshell.prototypes.console import ConsoleShell


def demo_ghost(root_path: str, root_container: Container) -> Ghost:
    """
    bootstrap demo ghost from local files in ./demo
    """
    container = root_container
    config_path = "/".join([root_path, "configs", "ghost"])
    runtime_path = "/".join([root_path, "runtime"])

    config_file = config_path + "/config.yml"
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    config = GhostConfig(**config_data)

    ghost = MockGhost(container, config, config_path, runtime_path)
    return ghost


def run_console_shell(root_path: str, root_container: Container):
    """
    run console shell with local demo ghost
    """
    container = root_container
    config_path = "/".join([root_path, "configs", "shells/console"])
    runtime_path = "/".join([root_path, "runtime"])
    # 分享相同的 path.
    shell = ConsoleShell(container, config_path, runtime_path)
    shell.bootstrap().run_as_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="run ghoshell console shell with local demo ghost")
    parser.add_argument(
        "--path", "-p",
        nargs="?",
        default="",
        help="relative directory path that include config and runtime directories",
        type=str,
    )
    parsed = parser.parse_args(sys.argv[1:])
    relative = str(parsed.path)

    cwd = os.getcwd()
    root_path = cwd.rstrip("/") + "/" + relative.lstrip("/")
    root_container = Container()

    # register logger
    with open(root_path + "/configs/logging.yaml", "r", encoding="utf-8") as f:
        logging_config = yaml.safe_load(f)
        dictConfig(logging_config)

    ghost = demo_ghost(root_path, root_container)
    ghost.boostrap()
    root_container.set(Ghost, ghost)
    run_console_shell(root_path, root_container)
