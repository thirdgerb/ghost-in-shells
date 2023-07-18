from __future__ import annotations

import json
import uuid
from typing import Dict, ClassVar

from ghoshell.contracts import Cache
from ghoshell.ghost import Session


class SessionImpl(Session):
    current_process_id_key: ClassVar[str] = "current_process_id"

    def __init__(
            self,
            cache: Cache,
            clone_id: str,
            session_id: str,
            expire: int,
    ):
        self._clone_id = clone_id
        self._cache = cache
        self._session_id = session_id
        self._expire = expire
        self._clear: bool = False

    @property
    def clone_id(self) -> str:
        return self._clone_id

    @property
    def session_id(self) -> str:
        return self._session_id

    def new_process_id(self) -> str:
        return uuid.uuid4().hex

    def current_process_id(self) -> str:
        session_key = self._session_cache_key()
        process_id = self._cache.get_member(session_key, self.current_process_id_key)
        if process_id is None:
            process_id = self.new_process_id()
            self._cache.set_member(session_key, self.current_process_id_key, process_id)
        return process_id

    def new_message_id(self) -> str:
        return uuid.uuid4().hex

    def clear_all(self) -> None:
        session_key = self._session_cache_key()
        self._cache.remove(session_key)
        self._clear = True

    def set(self, key: str, value: Dict) -> bool:
        cache_key = self._session_cache_key()
        return self._cache.set_member(cache_key, key, json.dumps(value))

    def get(self, key: str) -> Dict | None:
        cache_key = self._session_cache_key()
        value = self._cache.get_member(cache_key, key)
        if value is None:
            return None
        try:
            loads = json.loads(value, object_hook=dict)
            if isinstance(loads, Dict):
                return loads
        except AttributeError:
            pass
        return None

    def remove(self, *key: str) -> None:
        cache_key = self._session_cache_key()
        self._cache.remove_member(cache_key, *key)

    def lock(self, key: str, overdue: int = -1) -> bool:
        locker_key = self._session_locker_key(key)
        return self._cache.lock(locker_key, overdue)

    def _session_locker_key(self, key: str) -> str:
        return f"ghoshell:session:{self._session_id}:locker:{key}"

    def unlock(self, key: str) -> bool:
        locker_key = self._session_locker_key(key)
        return self._cache.unlock(locker_key)

    def _task_cache_key(self, tid: str):
        # 暂时定义为 session 级别的.
        return f"ghoshell:clone:{self._clone_id}:task:{tid}"

    def get_task_data(self, tid: str) -> Dict | None:
        key = self._task_cache_key(tid)
        val = self._cache.get(key)
        if val is not None:
            try:
                loads = json.loads(val)
                return loads
            except AttributeError:
                return None
        return None

    def set_task_data(self, tid: str, value: Dict, overdue: int) -> None:
        key = self._task_cache_key(tid)
        val = json.dumps(value)
        self._cache.set(key, val, overdue)

    def _session_cache_key(self) -> str:
        return f"ghost:clone:{self._clone_id}:session:{self._session_id}"

    def destroy(self) -> None:
        if not self._clear:
            session_key = self._session_cache_key()
            # 重置过期时间.
            self._cache.expire(session_key, self._expire)
        # del
        del self._cache
        del self._session_id
        del self._clone_id
