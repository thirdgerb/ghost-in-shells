from pydantic import BaseModel

from ghoshell.url import URL


class GhostConfig(BaseModel):
    name: str = "ghost"

    root_url: URL

    on_busy: str = "系统正在处理消息中... 请稍后"

    on_unexpected: str = "无法处理的消息"

    exception_traceback_limit: int = 5

    session_overdue: int = 1800

    process_max_tasks: int = 20
    process_lock_overdue: int = 30
