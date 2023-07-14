import json
import uuid
from typing import Dict, ClassVar

from ghoshell.contracts import Cache
from ghoshell.ghost import Session


class SessionImpl(Session):
    process_key: ClassVar[str] = "process_id"

    def __init__(self, cache: Cache, clone_id: str, session_id: str, expire: int):
        self._clone_id = clone_id
        self._cache = cache
        self._session_id = session_id
        self._expire = expire

    @property
    def clone_id(self) -> str:
        return self._clone_id

    @property
    def session_id(self) -> str:
        return self._session_id

    def new_process_id(self) -> str:
        return uuid.uuid4().hex

    def current_process_id(self) -> str:
        session_key = self._session_key()
        process_id = self._cache.get_member(session_key, self.process_key)
        if process_id is None:
            process_id = self.new_process_id()
            self._cache.set_member(session_key, self.process_key, process_id)
        return process_id

    def new_message_id(self) -> str:
        return uuid.uuid4().hex

    def set(self, key: str, value: Dict) -> bool:
        cache_key = self._session_key()
        return self._cache.set_member(cache_key, key, json.dumps(value))

    def get(self, key: str) -> Dict | None:
        cache_key = self._session_key()
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

    def _session_key(self) -> str:
        return f"ghost:clone:{self._clone_id}:session:{self._session_id}"

    def destroy(self) -> None:
        session_key = self._session_key()
        self._cache.expire(session_key, self._expire)
        # del
        del self._cache
        del self._session_id
        del self._clone_id
