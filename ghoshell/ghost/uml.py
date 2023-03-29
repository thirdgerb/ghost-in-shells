from typing import Dict

from pydantic import BaseModel


class UniformMindLocator(BaseModel):
    """
    思维座标, 用类似 URL 的方式来定义.
    """
    # 对应的 ghost 名, 对标 url 的 host. 为空则与上下文一致.
    ghost: str = ""

    # 对应的 Think 名, 对标 url 的 path. 用来标记一个 Think, 本质上是一个有限状态机.
    think: str = ""

    # Think 的一个状态，对标 url 的 fragment。
    stage: str = ""

    # 参数, 如果是需要入参的状态机, 不传入正确的参数可能会报错, 或者影响运转的初始状态.
    # 注意, 每个 Think 能力应该有自己的 arguments 协议.
    args: Dict = {}

    # def is_same(self, uml: "UniformMindLocator") -> bool:
    #     return (self.ghost == uml.ghost or uml.ghost == "") and self.think == uml.think

    def to_stage(self, stage: str) -> "UniformMindLocator":
        return UniformMindLocator(
            ghost=self.ghost,
            think=self.think,
            stage=stage,
            args=self.args.copy()
        )

    def new_args(self, args: Dict) -> "UniformMindLocator":
        return UniformMindLocator(
            ghost=self.ghost,
            think=self.think,
            stage=self.stage,
            args=args.copy()
        )

    # def is_same(self, other: "UML") -> bool:
    #     return (other.ghost == "" or self.ghost == "" or self.ghost == other.ghost) \
    #         and self.think == other.think \
    #         and self.stage == other.stage


UML = UniformMindLocator
