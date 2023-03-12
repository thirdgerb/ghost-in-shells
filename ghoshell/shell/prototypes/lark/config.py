from pydantic import BaseModel


class FeishuConfig(BaseModel):
    app_id: str
    app_secret: str

    app_isv: bool = False
    is_lark: bool = False
    verification_token: str = ""
    encrypt_key: str = ""

    event_webhook: str = "lark/webhook/event"


class FlaskConfig(BaseModel):
    app_host: str = "127.0.0.1"
    app_port: int = 19527


class LarkShellConfig(BaseModel):
    feishu: FeishuConfig
    flask: FlaskConfig
