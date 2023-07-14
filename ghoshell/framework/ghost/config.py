from pydantic import BaseModel

from ghoshell.url import URL


class GhostConfig(BaseModel):
    name: str = "ghost"

    root_url: URL

    exception_traceback_limit: int = 5

    session_overdue: int = 1800

    process_max_tasks: int = 20
    process_default_overdue: int = 1800
    process_lock_overdue: int = 30
