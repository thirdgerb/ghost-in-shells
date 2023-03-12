from pydantic import BaseModel


class UserInfo(BaseModel):
    union_id: str
    user_id: str
    open_id: str
