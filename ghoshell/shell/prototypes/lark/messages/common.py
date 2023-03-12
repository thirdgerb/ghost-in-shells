from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Header:
    event_id: str
    event_type: str
    create_time: str
    token: str
    app_id: str
    tenant_key: str


@dataclass_json
@dataclass
class UserInfo:
    union_id: str
    user_id: str
    open_id: str
