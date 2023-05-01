from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.ghost_fmk.contracts import RuntimeDriver
from ghoshell.ghost_fmk.runtime import CacheRuntimeDriver, Cache


class CacheRuntimeDriverProvider(Provider):
    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return RuntimeDriver

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        cache = con.force_fetch(Cache)
        return CacheRuntimeDriver(cache)
