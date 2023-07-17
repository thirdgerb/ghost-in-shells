from __future__ import annotations

from typing import List, Dict

from pydantic import BaseModel, Field


class Avatar(BaseModel):
    # "avatar_72": "https://foo.icon.com/xxxx",
    # "avatar_240": "https://foo.icon.com/xxxx",
    # "avatar_640": "https://foo.icon.com/xxxx",
    # "avatar_origin": "https://foo.icon.com/xxxx"
    avatar_72: str = ""
    avatar_240: str = ""
    avatar_640: str = ""
    avatar_origin: str = ""


class UserStatus(BaseModel):
    # "is_frozen": false,
    # "is_resigned": false,
    # "is_activated": true,
    # "is_exited": false,
    # "is_unjoin": false
    is_frozen: bool
    is_resigned: bool
    is_activated: bool
    is_exited: bool
    is_unjoin: bool


class DepartmentPathName(BaseModel):
    # "name": "测试部门名1",
    # "i18n_name": {
    #     "zh_cn": "测试部门名1",
    #     "ja_jp": "試験部署名 1",
    #     "en_us": "Testing department name 1"
    # }
    name: str = ""
    i18n_name: Dict[str, str] = Field(default_factory=lambda: {})


class DepartmentPath(BaseModel):
    # "department_ids": [
    #     "od-4e6ac4d14bcd5071a37a39de902c7141"
    # ],
    # "department_path_name": {
    #     "name": "测试部门名1",
    #     "i18n_name": {
    #         "zh_cn": "测试部门名1",
    #         "ja_jp": "試験部署名 1",
    #         "en_us": "Testing department name 1"
    #     }
    # }
    department_ids: List[str] = Field(default_factory=lambda: [])
    department_path_name: DepartmentPathName | None = None


class AssignInfo(BaseModel):
    # "subscription_id": "7079609167680782300",
    # "license_plan_key": "suite_enterprise_e5",
    # "product_name": "旗舰版 E5",
    # "i18n_name": {
    #     "zh_cn": "zh_cn_name",
    #     "ja_jp": "ja_jp_name",
    #     "en_us": "en_name"
    # },
    # "start_time": "1674981000",
    # "end_time": "1674991000"
    subscription_id: str = ""
    license_plan_key: str = ""
    product_name: str = ""
    i18n_name: Dict[str, str] = Field(default_factory=dict)
    start_time: int
    end_time: int


class CustomAttr(BaseModel):
    type: str = ""
    id: str = ""
    value: Dict = Field(default_factory=dict)


class UserOrder(BaseModel):
    # "department_id": "od-4e6ac4d14bcd5071a37a39de902c7141",
    # "user_order": 100,
    # "department_order": 100,
    # "is_primary_dept": true
    department_id: str
    user_order: int
    department_order: int
    is_primary_dept: bool


class UserIds(BaseModel):
    """
    每个用户的三种 ID
    """
    union_id: str = Field(description="用户的 union_id")
    user_id: str = Field(description="用户的 user_id")
    open_id: str = Field(description="用户的open_id")


class UserInfo(BaseModel):
    # "union_id": "on_94a1ee5551019f18cd73d9f111898cf2",
    # "user_id": "3e3cf96b",
    # "open_id": "ou_7dab8a3d3cdcc9da365777c7ad535d62",
    # "name": "张三",
    # "en_name": "San Zhang",
    # "nickname": "Alex Zhang",
    # "email": "zhangsan@gmail.com",
    # "mobile": "13011111111 (其他例子，中国大陆手机号: 13011111111 或 +8613011111111, 非中国大陆手机号:  +41446681800)",
    # "mobile_visible": false,
    # "gender": 1,
    # "leader_user_id": "ou_7dab8a3d3cdcc9da365777c7ad535d62",
    # "city": "杭州",
    # "country": "CN",
    # "work_station": "北楼-H34",
    # "join_time": 2147483647,
    # "is_tenant_manager": false,
    # "employee_no": "1",
    # "employee_type": 1,
    # "enterprise_email": "demo@mail.com",
    # "job_title": "xxxxx",
    # "job_level_id": "mga5oa8ayjlp9rb",
    # "job_family_id": "mga5oa8ayjlp9rb",

    union_id: str
    user_id: str
    open_id: str
    name: str
    en_name: str
    nickname: str
    email: str
    join_time: int
    mobile: str
    mobile_visible: bool
    gender: int
    leader_user_id: str
    city: str
    country: str
    work_station: str
    is_tenant_manager: bool = False
    employee_no: str = ""
    employee_type: int = 1
    enterprise_email: str = ""
    job_title: str = ""
    job_level_id: str = ""
    job_family_id: str = ""

    avatar: Avatar | None = None
    status: UserStatus | None = None
    orders: List[UserOrder] = Field(default_factory=list)
    department_ids: List[str] = Field(default_factory=list)
    custom_attrs: List[CustomAttr] = Field(default_factory=list)
    assign_info: List[AssignInfo] = Field(default_factory=list)
    department_path: DepartmentPath | None = None
