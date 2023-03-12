from flask import Flask, request, make_response, Response as FlaskResponse
from larksuiteoapi import DOMAIN_LARK_SUITE, DOMAIN_FEISHU, LEVEL_DEBUG
from larksuiteoapi.app_settings import AppSettings
from larksuiteoapi.consts import APP_TYPE_ISV, APP_TYPE_INTERNAL
from larksuiteoapi.event import handle_event, set_event_callback
from larksuiteoapi.model import OapiRequest, OapiResponse, OapiHeader

from ghoshell.ghost import Input, IGhost, Output
from ghoshell.shell import ShellFramework, IContext
from ghoshell.shell.prototypes.lark.config import LarkShellConfig
from ghoshell.shell.prototypes.lark.events import *

LARK_SHELL_KIND = "lark.shell"


class LarkContext(IContext):

    def __init__(
            self,
            req: OapiRequest,
            resp: OapiResponse,
            lark_ctx: Context,
            config: Config,
    ):
        self.req = req
        self.resp = resp
        self.lark_ctx = lark_ctx
        self.lark_config = config

    def send(self, _output: Output) -> None:
        pass

    def destroy(self) -> None:
        del self.req


class LarkShell(ShellFramework):

    def __init__(
            self,
            app_name: str,
            ghost: IGhost,
            config: LarkShellConfig
    ):
        self.app_name = app_name
        self.config = config
        self._ghost = ghost

        lark_settings = AppSettings(
            APP_TYPE_ISV if config.feishu.app_isv else APP_TYPE_INTERNAL,
            config.feishu.app_id,
            config.feishu.app_secret,
            verification_token=config.feishu.verification_token,
            encrypt_key=config.feishu.encrypt_key,
        )
        domain = DOMAIN_LARK_SUITE if config.feishu.is_lark else DOMAIN_FEISHU
        self.feishu_config = Config(domain, lark_settings, log_level=LEVEL_DEBUG)
        self.flask_app = Flask(self.app_name)

    def connect(self, inpt: Input) -> IGhost:
        return self._ghost

    def on_event(self, e: Any) -> Input:
        pass

    def context(self, _input: Input) -> LarkContext:
        pass

    def kind(self) -> str:
        return LARK_SHELL_KIND

    def run(self):
        # 注册消息处理
        self._init_lark()
        # 注册 flask 接口
        webhook = self.config.feishu.event_webhook
        self.flask_app.route(webhook, methods=['GET', 'POST'])
        # 运行
        self.flask_app.run(port=self.config.flask.app_port, host=self.config.flask.app_host)

    def register_lark_event_handler(self, event_type, callback: LARK_EVENT_HANDLER, event_class=dict):
        """
        方便为 shell 准备更多事件处理能力.
        """
        set_event_callback(self.feishu_config, event_type, callback, event_class)

    def webhook_event(self) -> FlaskResponse:
        """
        实现一个 lark 的基本 event handler
        """
        oapi_request = OapiRequest(uri=request.path, body=request.data, header=OapiHeader(request.headers))
        oapi_resp = handle_event(self.feishu_config, oapi_request)

        resp = make_response()
        resp.headers['Content-Type'] = oapi_resp.content_type
        resp.data = oapi_resp.body
        resp.status_code = oapi_resp.status_code
        return resp

    # ----- inner methods ----- #

    def _init_lark(self) -> None:
        pass

    def _handle_message_event(self, ctx: Context, conf: Config, event):
        pass
