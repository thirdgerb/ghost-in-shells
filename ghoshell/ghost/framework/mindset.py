from typing import Optional

from ghoshell.ghost import Mindset, Think
from ghoshell.ghost.mindset import ThinkMeta, ThinkDriver


class IMindset(Mindset):
    def fetch(self, thinking: str) -> Optional[Think]:
        pass

    def register_driver(self, key: str, driver: ThinkDriver) -> None:
        pass

    def register_meta(self, meta: ThinkMeta) -> None:
        pass
