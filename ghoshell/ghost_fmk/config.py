from pydantic import BaseModel

from ghoshell.ghost import Context, URL


class GhostConfig(BaseModel):
    root: URL
    process_max_tasks: int = 20
    process_default_overdue: int = 1800
    process_lock_overdue: int = 30

    @classmethod
    def instance(cls, ctx: Context) -> "GhostConfig":
        """
        实例化.
        """
        return cls(**ctx.clone.config)
