import logging
from logging import Logger, LoggerAdapter
from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.contracts import Cache
from ghoshell.framework.contracts import RuntimeDriver
from ghoshell.framework.contracts.think_meta_storage import ThinkMetaStorage
from ghoshell.framework.ghost.focus import FocusImpl
from ghoshell.framework.ghost.memory import Memory, MemoryImpl
from ghoshell.framework.ghost.mindset import MindsetImpl, LocalFileThinkMetaStorage
from ghoshell.framework.ghost.runtime import CacheRuntimeDriver
from ghoshell.ghost import Context, BootstrapException
from ghoshell.ghost import Mindset, Focus, Ghost


class CacheRuntimeDriverProvider(Provider):
    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return RuntimeDriver

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        cache = con.force_fetch(Cache)
        return CacheRuntimeDriver(cache)


class LocalThinkMetaStorageProvider(Provider):

    def __init__(self, relative_runtime_path: str = "think_metas"):
        self.relative_runtime_path = relative_runtime_path

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return ThinkMetaStorage

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        ghost = con.force_fetch(Ghost)
        runtime_path = ghost.runtime_path
        dirname = runtime_path.rstrip("/") + "/" + self.relative_runtime_path.lstrip("/")
        return LocalFileThinkMetaStorage(dirname)


class MindsetProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Mindset

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        driver = con.force_fetch(ThinkMetaStorage)
        focus = con.force_fetch(Focus)
        return MindsetImpl(driver, focus, None)


class MemoryProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Memory

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return MemoryImpl()


class ContextLoggerProvider(Provider):

    def __init__(self, logger_name: str = "ghoshell_context_logger"):
        self.logger_name = logger_name

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Logger

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        ctx = con.force_fetch(Context)
        if ctx.container.parent is None:
            raise BootstrapException("context container must be sub container of ghost")
        logger = logging.getLogger(self.logger_name)
        adapter = LoggerAdapter(logger, extra={"trace": ctx.input.trace.model_dump()})
        return adapter


class FocusProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Focus

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        return FocusImpl()
