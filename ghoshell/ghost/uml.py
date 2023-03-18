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

    # 参数, 如果是需要入参的状态机, 不传入正确的参数可能会报错, 或者影响运转的初始状态.
    # 注意, 每个 Think 能力应该有自己的 arguments 协议.
    args: Dict = {}


UML = UniformMindLocator
