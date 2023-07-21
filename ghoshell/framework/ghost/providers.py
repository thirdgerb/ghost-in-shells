from __future__ import annotations

import logging
from logging import LoggerAdapter
from typing import Dict, Type

from ghoshell.container import Provider, Container, Contract
from ghoshell.contracts import Cache
from ghoshell.framework.contracts.think_meta_storage import ThinkMetaStorage
from ghoshell.framework.ghost.config import GhostConfig
from ghoshell.framework.ghost.focus import FocusImpl
from ghoshell.framework.ghost.memory import Memory, MemoryImpl
from ghoshell.framework.ghost.mindset import MindsetImpl, LocalFileThinkMetaStorage
from ghoshell.framework.ghost.runtime import RuntimeImpl
from ghoshell.framework.ghost.session import SessionImpl
from ghoshell.ghost import Context, BootstrapError
from ghoshell.ghost import Mindset, Focus, Ghost, Session, Runtime


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
        return MindsetImpl(driver, None)


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
        return LoggerAdapter

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        ctx = con.force_fetch(Context)
        if ctx.container.parent is None:
            raise BootstrapError("context container must be sub container of ghost")
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


class SimpleAPIProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        pass

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        pass


class SessionProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Session

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        cache = con.force_fetch(Cache)
        config = con.force_fetch(GhostConfig)
        context = con.force_fetch(Context)
        session = SessionImpl(
            cache,
            clone_id=context.clone.clone_id,
            session_id=context.input.trace.session_id,
            expire=config.session_overdue,
        )
        return session


class RuntimeProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[Contract]:
        return Runtime

    def factory(self, con: Container, params: Dict | None = None) -> Contract | None:
        session = con.force_fetch(Session)
        config = con.force_fetch(GhostConfig)
        context = con.force_fetch(Context)
        runtime = RuntimeImpl(
            session,
            config.root_url,
            context.input.stateless,
            config.process_max_tasks,
            config.process_lock_overdue,
        )
        return runtime
