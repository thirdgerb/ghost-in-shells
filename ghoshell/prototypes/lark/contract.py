from __future__ import annotations

from abc import ABCMeta, abstractmethod

from ghoshell.prototypes.lark.types.consts import *
from ghoshell.prototypes.lark.types.user import UserInfo


class LarkSuite(metaclass=ABCMeta):

    @abstractmethod
    def get_access_token(self) -> str:
        pass

    @abstractmethod
    def get_tenant_token(self) -> str:
        pass

    @abstractmethod
    def get_user_info(
            self,
            user_id: str,
            user_id_type: str = UserIdType.OPEN_ID,
            department_id_type: str = DepartmentIdType.OPEN_DEPARTMENT_ID,
    ) -> UserInfo | None:
        pass
