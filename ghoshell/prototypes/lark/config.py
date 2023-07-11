# from larksuiteoapi import LEVEL_DEBUG
# from pydantic import BaseModel
#
#
# class LarkConfig(BaseModel):
#     """
#     lark 的配置
#     """
#     app_id: str
#     app_secret: str
#
#     app_isv: bool = False
#     is_lark: bool = False
#     verification_token: str = ""
#     encrypt_key: str = ""
#     log_level: int = LEVEL_DEBUG
#
#     event_webhook: str = "lark/webhook/event"
#
#
# class FlaskConfig(BaseModel):
#     """
#     flask 的配置
#     """
#     app_host: str = "127.0.0.1"
#     app_port: int = 19527
#
#
# class LarkShellConfig(BaseModel):
#     name: str = "lark_shell"
#     """
#     lark shell 的配置
#     """
#     lark: LarkConfig
#     flask: FlaskConfig
