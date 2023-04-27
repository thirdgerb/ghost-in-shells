from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.ghost import Mindset, Focus
from ghoshell.ghost_fmk.contracts import RuntimeDriver
from ghoshell.ghost_fmk.focus import FocusImpl
from ghoshell.ghost_fmk.memory import Memory, MemoryImpl
from ghoshell.ghost_fmk.mindset import MindsetImpl, ThinkMetaDriver
from ghoshell.ghost_fmk.runtime import CacheRuntimeDriver, Cache


class CacheRuntimeDriverProvider(Provider):
    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return RuntimeDriver

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        cache = con.force_fetch(Cache)
        return CacheRuntimeDriver(cache)


class FocusProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Focus

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return FocusImpl()


class MindsetProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Mindset

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        driver = con.force_fetch(ThinkMetaDriver)
        return MindsetImpl(driver, None)


class MemoryProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Memory

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return MemoryImpl()
