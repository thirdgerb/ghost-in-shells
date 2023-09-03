from __future__ import annotations

from typing import Dict, Optional, List

from pydantic import BaseModel, Field

from ghoshell.ghost import *


class _Init(BaseModel):
    """
    游戏初始化后的配置.
    """

    debug: bool = Field(description="是否开启 debug 模式. 开启后可以在运行时 debug. ", default=False)

    player_role: Dict[str, str] = Field(
        description="每个玩家随机分配到的角色",
        default_factory=dict,
    )

    user_player: str = Field(
        description="用户扮演的玩家, 为空意味着用户扮演观察者",
        default="",
    )


class _Event(BaseModel):
    """
    用事件的方式构成游戏的叙事.
    相当于小说里的段落.
    """

    description: str = Field(description="事件的描述, 真实的内容.", default="")
    visible: List[str] = Field(description="事件对哪些 player 而言是可见的.", default=list)


class _Turn(BaseModel):
    """
    回合描述.
    """
    day: int = Field(description="第几天", default=0)
    is_night: bool = Field(description="是否是白天", default=False)
    survivors: List[str] = Field(description="存活的人", default_factory=list)
    events: List[_Event] = Field(description="发生的事情", default_factory=list)


class WerewolfData(BaseModel):
    """
    狼人杀游戏的状态.
    """

    day: int = Field(description="第几天", default=0)

    inited: _Init = _Init()

    current: _Turn = _Turn()

    turns: List[_Turn] = Field(description="历史的回合的信息", default_factory=list)


class WerewolfGameThought(Thought):
    """
    狼人杀的游戏状态.
    """

    data: Optional[WerewolfData] = None

    def prepare(self, args: Dict) -> None:
        if self.data is None:
            self.data = WerewolfData()
        return

    def set_variables(self, variables: Dict) -> None:
        self.data = WerewolfData(**variables)

    def vars(self) -> Dict | None:
        return self.data.model_dump()
