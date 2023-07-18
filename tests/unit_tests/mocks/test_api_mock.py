from __future__ import annotations

from typing import Type

from ghoshell.contracts import APIArgs, APIResp, APICaller
from ghoshell.mocks.providers.api import APIRepositoryImpl


class Summary(APIResp):
    api_caller = "test/sum"

    sum: int


class SumArgs(APIArgs):
    api_caller = "test/sum"

    a: int
    b: int

    @classmethod
    def resp_type(cls) -> Type[Summary]:
        return Summary


class SumCaller(APICaller):

    @classmethod
    def args_type(cls) -> Type[APIArgs]:
        return SumArgs

    def call(self, args: SumArgs) -> APIResp:
        return Summary(sum=args.a + args.b)


def test_summary():
    repo = APIRepositoryImpl()
    repo.register_api(SumCaller())

    c = SumArgs(a=1, b=2)
    api = repo.get_api(c.api_caller)
    assert api is not None

    r1 = api.call(c)
    assert r1 is not None and r1.sum == 3

    r = Summary.call(repo, c)
    assert r is not None and r.sum == 3
