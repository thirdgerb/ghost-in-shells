# import json
# from os import path
# from typing import TYPE_CHECKING
#
# from ghoshell.shell.prototypes.lark.config import LarkShellConfig
#
# from ghoshell.framework.shell.shell import Bootstrapper
#
# if TYPE_CHECKING:
#     from ghoshell.shell.prototypes.lark.shell import LarkShell
#
#
# class BootLarkShellConfig(Bootstrapper):
#     """
#     加载运行时的配置.
#     """
#
#     def __init__(self, file_path: str = "lark.json"):
#         self.file_path: str = file_path
#
#     def bootstrap(self, shl: "LarkShell") -> None:
#         config = self.load_config(shl.pwd, self.file_path)
#         self.init_shell_config(shl, config)
#
#     @staticmethod
#     def load_config(pwd: str, file_path: str) -> LarkShellConfig:
#         """
#         读取相关配置. 都需要单测
#         """
#         file_path = path.join(pwd, file_path)
#         with open(file_path) as f:
#             data = f.read()
#             config_data = json.loads(data)
#             # 实例化 config
#             config = LarkShellConfig(**config_data)
#             return config
