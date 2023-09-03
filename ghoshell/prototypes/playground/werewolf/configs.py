from __future__ import annotations

from typing import List, Dict

from pydantic import BaseModel, Field


class Player(BaseModel):
    name: str = Field(description="角色名字")
    story: str = Field(description="角色的背景故事, 需要考虑出身, 性别等信息.")


class Role(BaseModel):
    name: str = Field(description="身份的标志")
    faction: str = Field(description="所属阵营")
    description: str = Field(description="身份的描述")
    strategy: str = Field(description="身份的博弈策略.")
    abilities: List[str] = Field(description="身份的能力", default_factory=list)


class Ability(BaseModel):
    name: str = Field(description="能力的名字")
    description: str = Field(description="能力的描述")


class Prompts(BaseModel):
    pass


class Speech(BaseModel):
    welcome: str = """
# 欢迎来到 GPT 狼人杀 Demo.

这是一个用 LLM 实现的狼人杀游戏, 参与玩家是 LLM 扮演的 AI 智能体.
您可以选择观察游戏的过程, 或者作为其中一名角色参与游戏.

由于游戏是由 AI 扮演, 所以系统等待输入时, 您可以输入任意信息进入下一步.
也可以输入 `/help` 查看可以使用的命令.
更多说明请看相关文档. 

这个 Demo 还是一个极简版本, 主要还是为了验证 LLM 的博弈能力. 
想要让它变得更完善的话, 请联系我.  
"""
    inited: str = "...完成了游戏初始化, 分配了玩家角色"
    invite_user: str = "本局游戏的参与者有: {players}. \n\n请问您是否想扮演其中的一人? 想的话请输入角色的名字, 不想的话输入空."
    invalid_input: str = "输入内容不合法"
    invalid_config: str = "系统配置异常"


class WerewolfGameConfig(BaseModel):
    """
    狼人杀游戏配置.
    """
    think: str = Field(description="think id")
    desc: str = Field(description="think 的描述")

    introduce: str = Field(description="游戏规则的描述")
    # 正经配置.
    story: str = Field(description="游戏背景介绍")
    players: List[Player] = Field(description="游戏中的参与者")
    roles: List[Role] = Field(description="游戏里的角色")
    abilities: List[Ability] = Field(description="游戏里的各种能力")
    game_roles: Dict[str, int] = Field(description="游戏里各种角色的数量")
    prompts: Prompts = Field(description="游戏运行过程中默认的 prompts")
    speech: Speech = Field(description="游戏的系统话术", default_factory=Speech)
    llm_config: str = Field(description="使用的 LLM 模型配置名, 比如 gpt-4-0613")
