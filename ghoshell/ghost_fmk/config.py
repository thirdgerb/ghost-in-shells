from pydantic import BaseModel

from ghoshell.ghost import URL


class GhostConfig(BaseModel):
    root_url: URL
    process_max_tasks: int = 20
    process_default_overdue: int = 1800
    process_lock_overdue: int = 30
