#!/usr/bin/env python
import os.path
from logging.config import dictConfig

import yaml
from rich.prompt import Prompt

from ghoshell.container import Container
from ghoshell.framework.ghost import GhostConfig
from ghoshell.framework.shell import SyncGhostMessenger, MessageQueue
from ghoshell.ghost import Ghost
from ghoshell.mocks import MockGhost, MockMessageQueueProvider
from ghoshell.prototypes import ConsoleShell, BaiduSpeechShell, SpheroBoltShell
from ghoshell.shell import Messenger

pwd = os.getcwd()
root_path = pwd + "/demo"

root_container = Container()

# register logger
with open(root_path + "/configs/logging.yaml", "r", encoding="utf-8") as f:
    logging_config = yaml.safe_load(f)
    dictConfig(logging_config)


def demo_ghost() -> Ghost:
    """
    bootstrap demo ghost from local files in ./demo
    """
    container = root_container
    container.register(MockMessageQueueProvider())
    config_path = "/".join([root_path, "configs", "ghost"])
    runtime_path = "/".join([root_path, "runtime"])

    config_file = config_path + "/config.yml"
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    config = GhostConfig(**config_data)

    ghost = MockGhost(container, config, config_path, runtime_path)
    return ghost


def run_console_shell():
    """
    run console shell with local demo ghost
    """
    container = root_container
    config_path = "/".join([root_path, "configs", "shells/console"])
    runtime_path = "/".join([root_path, "runtime"])
    # 分享相同的 path.
    shell = ConsoleShell(container, config_path, runtime_path)
    shell.bootstrap().run_as_app()


def run_sphero_shell():
    """
    run console shell with local demo ghost
    """
    container = root_container
    config_path = "/".join([root_path, "configs", "shells/sphero"])
    runtime_path = "/".join([root_path, "runtime"])
    # 分享相同的 path.
    shell = SpheroBoltShell(container, config_path, runtime_path)
    shell.bootstrap().run_as_app()


def run_speech_shell():
    container = root_container
    config_path = "/".join([root_path, "configs", "shells/baidu_speech"])
    runtime_path = "/".join([root_path, "runtime"])
    shell = BaiduSpeechShell(container, config_path, runtime_path)
    shell.bootstrap().run_as_app()


shells = {
    "console": run_console_shell,
    "speech": run_speech_shell,
    "sphero": run_sphero_shell,
}

default_shell = "console"


def main() -> None:
    ghost = demo_ghost()
    ghost.boostrap()
    message_queue = ghost.container.force_fetch(MessageQueue)
    messenger = SyncGhostMessenger(ghost, queue=message_queue)
    root_container.set(Messenger, messenger)
    root_container.set(Ghost, ghost)

    demo_shell_chosen = Prompt.ask("choose demo shell", choices=[key for key in shells.keys()], default=default_shell)
    if demo_shell_chosen not in shells:
        print(f"invalid [{demo_shell_chosen}] provided")
        exit(0)

    runner = shells[demo_shell_chosen]
    runner()


if __name__ == "__main__":
    main()
