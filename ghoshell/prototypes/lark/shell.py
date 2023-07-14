# from typing import Callable, Any
# from typing import Dict
#
# from flask import Flask, request, make_response, Response as FlaskResponse
# from ghoshell.shell.prototypes.lark.bootstraps import BootLarkShellConfig
# from ghoshell.shell.prototypes.lark.config import LarkShellConfig
# from ghoshell.shell.prototypes.lark.event_pipes import ParseLarkEventToInputPipe
# from ghoshell.shell.prototypes.lark.events import EVENTS_MAP
# from ghoshell.shell.prototypes.lark.suite import LarkSuite
# from larksuiteoapi import Config, DOMAIN_LARK_SUITE, DOMAIN_FEISHU
# from larksuiteoapi import Context
# from larksuiteoapi.app_settings import AppSettings
# from larksuiteoapi.consts import APP_TYPE_ISV, APP_TYPE_INTERNAL
# from larksuiteoapi.event import handle_event, set_event_callback
# from larksuiteoapi.model import OapiRequest, OapiHeader
# from pydantic import BaseModel
#
# from ghoshell.ghost import Input, Ghost, Output
# from ghoshell.shell import ShellKernel, IShellContext
#
# LARK_SHELL_KIND = "lark.shell"
# LARK_EVENT_HANDLER = Callable[[], Any]
#
#
# class LarkEventCaller:
#     """
#     对 lark 消息的基本封装.
#     """
#
#     def __init__(self, ctx: Context, conf: Config, event: Dict):
#         self.ctx = ctx
#         self.conf = conf
#         self.event = event
#         self.event_type = event.get("header", {}).get("event_type", "")
#
#
# class LarkContext(IShellContext):
#
#     def __init__(
#             self,
#             _input: Input,
#             suite: LarkSuite,
#     ):
#         self.lark_suite = suite
#         self.input = _input
#         self.ctx = Context()
#
#     def send(self, _output: Output) -> None:
#         for msg in _output.as_payload:
#             pass
#
#     def destroy(self) -> None:
#         del self.lark_suite
#         del self.input
#
#
# class LarkShellEnv(BaseModel):
#     event: Dict = {}
#
#
# class LarkShell(ShellKernel):
#     """
#     lark 封装成 shell
#     """
#
#     # 运行目录
#     pwd: str
#     # 运行 flask app 名字
#     app_name: str
#     # ghost 的实现.
#     ghost: Ghost = None
#
#     # bootstrap
#     lark_config: Config = None
#     flask_app: Flask = None
#     config: LarkShellConfig = None
#     lark_suite: LarkSuite = None
#
#     # --- implements attributes --- #
#
#     # 启动流程
#     bootstrapping = [
#         BootLarkShellConfig(),
#     ]
#
#     # 消息解析流程.
#     event_middleware = [
#         ParseLarkEventToInputPipe(),
#     ]
#
#     input_middleware = []
#     output_middleware = []
#
#     def __init__(
#             self,
#             app_name: str,
#             pwd: str,
#             ghost: Ghost,
#     ):
#         self.pwd = pwd
#         self.app_name = app_name
#         self._ghost = ghost
#         # 更多的初始化依赖 bootstrapping 的实现.
#
#     def connect(self, inpt: Input) -> Ghost:
#         """
#         可以重写这个方法, 去定义获取 ghost 的逻辑.
#         """
#         return self._ghost
#
#     def context(self, _input: Input) -> LarkContext:
#         return LarkContext(
#             _input=_input,
#             suite=self.lark_suite,
#         )
#
#     def kind(self) -> str:
#         return self.config._name if self.config._name else LARK_SHELL_KIND
#
#     def run(self):
#         # 注册消息处理
#         self._init_lark_default_event_handlers()
#         # 注册 flask 接口
#         webhook = self.config.lark.event_webhook
#         self.flask_app.route(webhook, methods=['GET', 'POST'])
#         # 运行
#         self.flask_app.run(port=self.config.flask.app_port, host=self.config.flask.app_host)
#
#     # ----- lark abilities ----- #
#
#     def register_lark_event_handler(self, event_type, callback: LARK_EVENT_HANDLER, event_class=dict):
#         """
#         方便为 shell 准备更多事件处理能力.
#         默认只提供消息响应事件.
#         """
#         set_event_callback(self.lark_config, event_type, callback, event_class)
#
#     def webhook_event(self) -> FlaskResponse:
#         """
#         实现一个 lark 的基本 event handler
#         """
#         oapi_request = OapiRequest(uri=request.path, body=request.data, header=OapiHeader(request.headers))
#         oapi_resp = handle_event(self.lark_config, oapi_request)
#
#         resp = make_response()
#         resp.headers['Content-Type'] = oapi_resp.content_type
#         resp.data = oapi_resp.body
#         resp.status_code = oapi_resp.status_code
#         return resp
#
#     # ----- register defaults event handler ----- #
#
#     def _init_shell_config(self, config: LarkShellConfig):
#         """
#         初始化 shell 的配置.
#         """
#         self.config = config
#         lark_settings = AppSettings(
#             APP_TYPE_ISV if config.lark.app_isv else APP_TYPE_INTERNAL,
#             config.lark.app_id,
#             config.lark.app_secret,
#             verification_token=config.lark.verification_token,
#             encrypt_key=config.lark.encrypt_key,
#         )
#         domain = DOMAIN_LARK_SUITE if config.lark.is_lark else DOMAIN_FEISHU
#         lark_config = Config(domain, lark_settings, log_level=self.config.lark.log_level)
#         self.lark_suite = LarkSuite(lark_config)
#         self.flask_app = Flask(self.app_name)
#
#     def _init_lark_default_event_handlers(self) -> None:
#         """
#         注册默认的消息回调.
#         """
#         for event_type in EVENTS_MAP.keys():
#             self.register_lark_event_handler(event_type, self._handle_message_event)
#
#     def _handle_message_event(self, ctx: Context, conf: Config, event: Dict):
#         """
#         简单封装一下, 响应 lark 的事件.
#         """
#         caller = LarkEventCaller(ctx, conf, event)
#         self.tick(caller)
