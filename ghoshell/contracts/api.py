from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Type, Dict, Iterator, ClassVar

from pydantic import BaseModel


class APIArgs(BaseModel, metaclass=ABCMeta):
    """
    API 的参数类定义.
    """
    api_caller: ClassVar[str] = ""


class APIResp(BaseModel, metaclass=ABCMeta):
    """
    API 的返回值定义.
    """
    api_caller: ClassVar[str] = ""


class APIError(RuntimeError):
    """
    API 接口调用异常.
    """

    def __init__(self, code: int, message: str, suggestion: str = ""):
        self.code = code
        self.message = message
        self.suggestion = suggestion
        super().__init__()


class APICaller(metaclass=ABCMeta):
    """
    一个标准的 API 的封装.
    """

    @classmethod
    @abstractmethod
    def args_type(cls) -> Type[APIArgs]:
        pass

    @classmethod
    @abstractmethod
    def resp_type(cls) -> Type[APIResp]:
        pass

    @abstractmethod
    def call(self, args: APIArgs) -> APIResp | None:
        """
        :raise APIError
        """
        pass

    def vague_call(self, args: Dict) -> Dict | None:
        args = self.args_type()(**args)
        resp = self.call(args)
        if resp is not None:
            return resp.model_dump()
        return None


class APIRepository(metaclass=ABCMeta):
    """
    存放所有 API 的容器.
    还需要和测试用例结合到一起.
    """

    def vague_call(self, api_caller: str, args: Dict) -> Dict | None:
        api = self.get_api(api_caller)
        if api is None:
            raise ImportError(f"api caller {api_caller} not found")
        return api.vague_call(args)

    def call(self, args: APIArgs) -> APIResp | None:
        api = self.get_api(args.api_caller)
        if api is None:
            raise ImportError(f"api caller {args.api_caller} not found")
        return api.call(args)

    @abstractmethod
    def get_api(self, namespace: str) -> APICaller | None:
        pass

    @abstractmethod
    def register_api(self, api: APICaller) -> None:
        pass

    @abstractmethod
    def foreach_api(self) -> Iterator[APICaller]:
        pass
