from __future__ import annotations

import hashlib
from typing import Dict, List, Any, Set

from pydantic import BaseModel, Field


class UniformResolverLocator(BaseModel):
    """
    思维座标, 用类似 URL 的方式来定义.
    """

    # 对应的 Resolver 名, 对标 url 的 path. 用来标记一个 Resolver, 本质上是一个有限状态机.
    think: str

    # Resolver 的一个状态，对标 url 的 fragment。
    stage: str = ""

    # 参数, 如果是需要入参的状态机, 不传入正确的参数可能会报错, 或者影响运转的初始状态.
    # 注意, 每个 Resolver 能力应该有自己的 arguments 协议.
    args: Dict[str, Any] = Field(default_factory=lambda: {})

    # def is_same(self, url: "UniformMindLocator") -> bool:
    #     return (self.ghost == url.ghost or url.ghost == "") and self.Resolver == url.Resolver
    @classmethod
    def new(cls, think: str, stage: str = "", args: Dict | None = None):
        if args is None:
            args = {}
        return URL(think=think, stage=stage, args=args)

    def copy_with(self, stage: str | None = None, args: Dict | None = None) -> "URL":
        if stage is None:
            stage = self.stage
        if args is None:
            args = self.args.copy()
        return UniformResolverLocator(
            think=self.think,
            stage=stage,
            args=args,
        )

    def to_dict(self, stage: str | None = None, args: Dict | None = None) -> Dict:
        result = self.model_dump()
        if stage is not None:
            result["stage"] = stage
        if args is not None:
            result["args"] = args.copy()
        return result

    def to_stages(self, *stages: str) -> List["URL"]:
        result = []
        for stage in stages:
            url = self.copy_with(stage=stage)
            result.append(url)
        return result

    @classmethod
    def new_think(cls, think) -> "UniformResolverLocator":
        return cls(think=think)

    def new_id(
            self,
            extra: Dict[str, str] | None = None,  # 加入额外的参数, 通常是 context.input.trace 相关参数.
            enums: Set[str] | None = None,  # 加入额外的常量, 用来生成唯一 id.
            args: bool = False,  # 将入参也作为生成唯一 id 的变量.
    ) -> str:
        """
        提供一个默认的方法用来生成一个 id.
        """
        extra_str = ""
        if extra is not None:
            keys = extra.keys()
            sort = sorted(keys)
            for key in sort:
                extra_str += f"&{key}={extra[key]}"
        enums_str = "&enums[]="
        if enums is not None:
            keys = list(enums)
            keys = sorted(keys)
            enums_str += ",".join(keys)
        args_str = ""
        if args and self.args:
            keys = self.args.keys()
            sort = sorted(keys)
            for key in sort:
                args_str += f"&{key}={self.args[key]}"

        template = f"{self.think}::{self.stage}?{extra_str}::{args_str}::{enums_str}"
        return hashlib.md5(template.encode()).hexdigest()

    # def is_same(self, other: "url") -> bool:
    #     return (other.ghost == "" or self.ghost == "" or self.ghost == other.ghost) \
    #         and self.Resolver == other.Resolver \
    #         and self.stage == other.stage


URL = UniformResolverLocator
