from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ghoshell.ghost import Thought
from ghoshell.prototypes.playground._werewolf.configs import Player, Prompts


class Status(BaseModel):
    survivors: List[str] = Field(
        description="存活的人",
    )
    events: List[str] = Field(
        description="发生的事件, 用自然语言描述",
    )


class Statement(BaseModel):
    thought: str = Field(description="说话前的思考")
    statement: str = Field(description="个人的发言")


class Daytime(BaseModel):
    """
    白天的记录.
    """
    players: List[str] = Field(description="活着的人名")
    scene: str = Field(description="早上起来时看到的场景")
    statements: Dict[str, Statement] = Field(description="每个人的发言", default_factory=dict)
    votes: Dict[str, str] = Field(description="角色投票情况", default_factory=dict)
    executed: str = Field(description="被处决的人", default="")


class Action(BaseModel):
    """
    一个动作.
    """
    act: str = Field(description="作出的动作")
    target: str = Field(description="动作的对象", default="")


class Night(BaseModel):
    """
    晚上发生的事情.
    """
    players: List[str] = Field(description="夜晚开始时活着的人", default_factory=list)
    survivors: List[str] = Field(description="结束时的人", default_factory=list)
    actor: str = ""
    actions: Dict[str, Action] = Field(description="夜间发生的事件", default_factory=dict)

    def night_description_prompt(self, prompts: Prompts) -> str:
        """
        描述夜间发生了什么.
        """
        pass


class Day(BaseModel):
    """
    一整天.
    """
    round: int = Field(description="第几天", default=0)
    daytime: Optional[Daytime] = Field(description="白天发生的事情", default=None)
    night: Optional[Night] = Field(description="夜晚发生的事情", default=None)


class GameResult(BaseModel):
    """
    游戏结果. 暂时不做总结了.
    """
    description: str = Field(description="胜负判断的原因")
    survivors: List[str] = Field(description="存活的人")


class GameData(BaseModel):
    """
    游戏的状态.
    """

    players: List[Player] = Field(
        description="参与游戏的玩家与身份",
        default_factory=list,
    )

    instruction: str = Field(
        description="游戏的开场介绍",
        default="",
    )

    current_day: Optional[Day] = Field(
        description="当前进行中的天",
        default=None,
    )

    days: List[Day] = Field(
        description="发生的剧情过程",
        default_factory=list,
    )

    events: List[str] = Field(
        description="发生的事件全部记录",
        default_factory=list,
    )

    result: Optional[GameResult] = Field(
        description="游戏的结局.",
        default=None,
    )


class WerewolfGameThought(Thought):
    """
    狼人杀游戏状态.
    """

    data: GameData

    def prepare(self, args: Dict) -> None:
        self.data = GameData()

    def set_variables(self, variables: Dict) -> None:
        self.data = GameData(**variables)

    def vars(self) -> Dict | None:
        return self.data.model_dump()
