from __future__ import annotations

from typing import Type

from ghoshell.contracts import APIArgs, APIResp, APICaller
from ghoshell.mocks.providers.api import APIRepositoryImpl


class SumArgs(APIArgs):
    api_caller = "test/sum"

    a: int
    b: int


class Summary(APIResp):
    api_caller = "test/sum"

    sum: int


class SumCaller(APICaller):

    @classmethod
    def args_type(cls) -> Type[APIArgs]:
        return SumArgs

    @classmethod
    def resp_type(cls) -> Type[APIResp]:
        return Summary

    def call(self, args: SumArgs) -> APIResp | None:
        return Summary(sum=args.a + args.b)


def test_summary():
    repo = APIRepositoryImpl()
    repo.register_api(SumCaller())

    c = SumArgs(a=1, b=2)
    api = repo.get_api(c.api_caller)
    assert api is not None

    r: Summary | None = api.call(c)
    assert r is not None and r.sum == 3

    value = repo.vague_call(c.api_caller, c.model_dump())
    assert value is not None and value.get("sum") == 3

    r = repo.call(c)
    assert r is not None and r.sum == 3
