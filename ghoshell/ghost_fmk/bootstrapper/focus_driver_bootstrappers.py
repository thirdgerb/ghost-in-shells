import yaml

from ghoshell.ghost import *
from ghoshell.ghost_fmk import Bootstrapper
from ghoshell.ghost_fmk.intentions import CommandFocusDriver
from ghoshell.ghost_fmk.intentions import LLMToolsFocusDriver, LLMToolsFocusConfig
from ghoshell.llms import LLMPrompter


class CommandFocusDriverBootstrapper(Bootstrapper):
    """
    注册命令行解析能力的驱动.
    """

    def bootstrap(self, ghost: Ghost):
        focus = ghost.focus

        # register command driver
        command_driver = CommandFocusDriver()
        ghost.container.set(CommandFocusDriver, command_driver)
        # 注册一个单例.
        focus.register(command_driver)


class LLMToolsFocusDriverBootstrapper(Bootstrapper):

    def __init__(self, relative_file_name: str = "nlu/llm_tools_config.yaml"):
        self.relative_file_name = relative_file_name

    def _load_config(self, ghost: Ghost) -> LLMToolsFocusConfig:
        filename = ghost.config_path.rstrip("/") + "/" + self.relative_file_name.lstrip("/")
        with open(filename) as f:
            data = yaml.safe_load(f)
            return LLMToolsFocusConfig(**data)

    def bootstrap(self, ghost: Ghost):
        config = self._load_config(ghost)
        focus = ghost.focus
        prompter = ghost.container.force_fetch(LLMPrompter)
        # register command driver
        driver = LLMToolsFocusDriver(config, prompter)
        ghost.container.set(LLMToolsFocusDriver, driver)
        # 注册一个单例.
        focus.register(driver)
