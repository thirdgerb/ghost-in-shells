from typing import Any, Callable

from flask import Flask, request
from flask.helpers import make_response
from larksuiteoapi import Context, Config, DOMAIN_LARK_SUITE, LEVEL_DEBUG
from larksuiteoapi.app_settings import AppSettings
from larksuiteoapi.consts import APP_TYPE_ISV, APP_TYPE_INTERNAL
from larksuiteoapi.event import handle_event, set_event_callback
from larksuiteoapi.service.contact.v3 import OapiRequest, OapiResponse

from ghoshell.ghost import Input, IGhost, Output
from ghoshell.shell import ShellFramework, IContext

from .events import IM_MESSAGE_RECEIVE

LARK_SHELL_KIND = "lark_shell"



class LarkShellConfig:
    lark_app_id: str
    lark_app_secret: str

    lark_app_isv: bool = False
    lark_verification_token: str = ""
    lark_encrypt_key: str = ""

    lark_event_webhook: str = "lark/webhook/event"
    flask_app_host: str = "127.0.0.1"
    flask_app_port: int = 19527


class LarkContext(IContext):

    def __init__(
            self,
            req: OapiRequest,
            resp: OapiResponse,
            lark_ctx: Context,
            lark_config: Config,
    ):
        self.req = req
        self.resp = resp
        self.lark_ctx = lark_ctx
        self.lark_config = lark_config

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
            APP_TYPE_ISV if config.lark_app_isv else APP_TYPE_INTERNAL,
            config.lark_app_id,
            config.lark_app_secret,
            verification_token=config.lark_verification_token,
            encrypt_key=config.lark_encrypt_key,
        )
        self.lark_config = Config(DOMAIN_LARK_SUITE, lark_settings, log_level=LEVEL_DEBUG)
        self.flask = Flask(self.app_name)

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
        webhook = self.config.lark_event_webhook
        self.flask.route(webhook, methods=['GET', 'POST'])
        # 运行
        self.flask.run(port=self.config.flask_app_port, host=self.config.flask_app_host)

    def register_lark_event_handler(self, event_type, callback: LARK_EVENT_CALLBACK):
        """
        方便为 shell 准备更多事件处理能力.
        """
        set_event_callback(self.lark_config, event_type, callback)

    def webhook_event(self):
        """
        实现一个 lark 的基本 event handler
        """
        oapi_request = OapiRequest(uri=request.path, body=request.data, header=OapiHeader(request.headers))
        resp = make_response()
        oapi_resp = handle_event(self.lark_config, oapi_request)
        resp.headers['Content-Type'] = oapi_resp.content_type
        resp.data = oapi_resp.body
        resp.status_code = oapi_resp.status_code
        return resp


    def _init_lark(self):

