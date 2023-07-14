from typing import Any, Dict

from ghoshell.ghost import Memory, MemoryDriver, Memo


class MemoryImpl(Memory):

    def __init__(self):
        self._drivers: Dict[str, MemoryDriver] = {}
        self._clone_id: str | None = None

    def clone(self, clone_id: str) -> Memory:
        copied = MemoryImpl()
        copied._drivers = self._drivers.copy()
        copied._clone_id = clone_id
        return copied

    def memorize(self, memo: Memo) -> None:
        kind = memo.KIND
        if kind in self._drivers:
            driver = self._drivers[kind]
            driver.save(memo)

    def recall(self, kind: str, index: Any) -> Memo | None:
        if kind in self._drivers:
            driver = self._drivers[kind]
            return driver.recall(index)

    def register(self, driver: MemoryDriver) -> None:
        self._drivers[driver.kind()] = driver

    def destroy(self) -> None:
        if self._clone_id:
            del self._drivers
