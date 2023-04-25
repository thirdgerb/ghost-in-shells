import hashlib
from typing import Dict, List, Any

from pydantic import BaseModel, Field


class UniformResolverLocator(BaseModel):
    """
    思维座标, 用类似 URL 的方式来定义.
    """

    # 对应的 Resolver 名, 对标 url 的 path. 用来标记一个 Resolver, 本质上是一个有限状态机.
    resolver: str

    # Resolver 的一个状态，对标 url 的 fragment。
    stage: str = ""

    # 参数, 如果是需要入参的状态机, 不传入正确的参数可能会报错, 或者影响运转的初始状态.
    # 注意, 每个 Resolver 能力应该有自己的 arguments 协议.
    args: Dict[str, Any] = Field(default_factory=lambda: {})

    # def is_same(self, url: "UniformMindLocator") -> bool:
    #     return (self.ghost == url.ghost or url.ghost == "") and self.Resolver == url.Resolver
    @classmethod
    def new(cls, resolver: str, stage: str, args: Dict):
        return URL(resolver=resolver, stage=stage, args=args)

    def copy_with(self, stage: str | None = None, args: Dict | None = None) -> "URL":
        if stage is None:
            stage = self.stage
        if args is None:
            args = self.args.copy()
        return UniformResolverLocator(
            resolver=self.resolver,
            stage=stage,
            args=args,
        )

    def to_dict(self, stage: str | None = None, args: Dict | None = None) -> Dict:
        result = self.dict()
        if stage is not None:
            result["stage"] = stage
        if args is not None:
            result["args"] = args.copy()
        return result

    def new_stages(self, *stages: str) -> List["URL"]:
        result = []
        for stage in stages:
            url = self.copy_with(stage=stage)
            result.append(url)
        return result

    def new_id(self, extra: Dict[str, str] = None, includes: set = None, args: bool = False) -> str:
        """
        提供一个默认的方法用来生成一个 id.
        """
        extra_str = ""
        if extra is not None:
            keys = extra.keys()
            sort = sorted(keys)
            for key in sort:
                if includes is not None and key not in includes:
                    continue
                extra_str += f"&{key}={extra[key]}"
        args_str = ""
        if args and self.args:
            keys = self.args.keys()
            sort = sorted(keys)
            for key in sort:
                args_str += f"&{key}={self.args[key]}"

        template = f"{self.resolver}::{self.stage}?{extra_str}::{args_str}"
        return hashlib.md5(template).hexdigest()

    # def is_same(self, other: "url") -> bool:
    #     return (other.ghost == "" or self.ghost == "" or self.ghost == other.ghost) \
    #         and self.Resolver == other.Resolver \
    #         and self.stage == other.stage


URL = UniformResolverLocator
