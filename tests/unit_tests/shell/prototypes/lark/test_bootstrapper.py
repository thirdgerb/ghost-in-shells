import os

from ghoshell.shell.prototypes.lark.bootstraps import BootLarkShellConfig


def test_boot_lark_shell_config():
    """
    测试 bootstrap 读取 config
    python 不熟悉
    """
    config = BootLarkShellConfig.load_config(os.path.dirname(__file__), "test.json")
    assert config.lark.app_id == "app_id"
    assert config.flask.app_port == 19527
