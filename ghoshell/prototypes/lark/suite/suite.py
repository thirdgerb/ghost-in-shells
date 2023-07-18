from __future__ import annotations

import json
from abc import ABCMeta, abstractmethod
from typing import ClassVar, List, Dict, Type
from urllib.parse import urlencode

import requests
from pydantic import BaseModel

from ghoshell.contracts import APICaller, APIArgs, APIResp


class LarkOpenAPIData(APIResp, metaclass=ABCMeta):
    api_caller: ClassVar[str] = "lark/openapi/caller"


class LarkOpenAPIArg(APIArgs, metaclass=ABCMeta):
    api_caller: ClassVar[str] = "lark/openapi/caller"

    # openapi 接口的请求方法.
    http_method: ClassVar[str] = "POST"

    # openapi 接口的地址.
    http_url: ClassVar[str] = ""

    # 定义哪几个参数需要放到 query 中, 哪些放到 body 中.
    query_args: ClassVar[List[str]] = []

    def http_queries(self) -> Dict:
        queries = {}
        if self.http_method == "GET":
            queries = self.model_dump()
        elif self.query_args:
            for key in self.query_args:
                value = getattr(self, key)
                if value is not None:
                    queries[key] = value
        return queries

    def http_payload(self) -> Dict | None:
        if self.http_method == "POST":
            payload = self.model_dump()
            for key in self.query_args:
                if key in payload:
                    del payload[key]
            return payload
        else:
            return None

    @classmethod
    @abstractmethod
    def resp_type(cls) -> Type[LarkOpenAPIData]:
        pass


class LarkOpenAPIResp(BaseModel):
    """
    接口请求的标准返回值.
    """

    code: int
    msg: str
    data: Dict


class LarkSuite(APICaller):

    @classmethod
    def args_type(cls) -> Type[APIArgs]:
        return LarkOpenAPIArg

    def openapi_headers(self) -> Dict:
        return {}

    def call(self, args: LarkOpenAPIArg) -> LarkOpenAPIData:
        queries = args.http_queries()
        payload = args.http_payload()
        headers = self.openapi_headers()
        url = args.http_url
        if queries:
            encoded_queries = urlencode(queries)
            url = url + '?' + encoded_queries

        data = None
        if payload:
            data = json.dumps(payload)

        resp = requests.request(
            method=args.http_method,
            url=url,
            headers=headers,
            data=data,
        )

        self._record_resp(args, resp)
        return self._handle_resp(resp, args.resp_type())

    def _handle_resp(self, resp: requests.Response, resp_type: Type[LarkOpenAPIData]) -> LarkOpenAPIData:
        resp_data = json.loads(resp.content)
        if resp.status_code != 200:
            self.raise_api_error(resp)
        data = resp_type(**resp_data.get("data", {}))
        return data

    @abstractmethod
    def _record_resp(self, args: LarkOpenAPIArg, resp: requests.Response):
        pass

    def raise_api_error(self, resp: requests.Response):
        pass
