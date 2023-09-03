from typing import List

from pydantic import BaseModel, Field


class Role:
    """
    角色常量
    """
    VILLAGER = "villager"
    SEER = "seer"
    WEREWOLF = "werewolf"
    WITCH = "witch"

    HAS_ABILITIES = {"seer", "werewolf", "witch"}


class Camp:
    HUMAN = "human"
    WEREWOLF = "werewolf"

    camps = {
        "human": {Role.VILLAGER, Role.SEER, Role.WITCH},
        "werewolf": {Role.WEREWOLF},
    }


class Player(BaseModel):
    """
    玩家的定义.
    """
    name: str = Field(description="玩家的名字")
    gender: str = Field(description="玩家的性别")
    personality: str = Field(
        description="角色的性格, 思维倾向的描述.",
    )
    background_story: str = Field(
        description="角色的背景故事, 主要描述他和其它角色的关系"
    )
    role: str = Field(
        description="游戏里分配到的身份",
        default="",
    )


class RoleInfo(BaseModel):
    """
    角色的信息.
    """
    name: str = Field(description="角色 id, 需要对应的角色 stage 存在.")
    description: str = Field(description="角色的描述")
    strategy: str = Field(description="角色的策略")


class SpeechCraft(BaseModel):
    """
    预设的话术.
    """

    werewolves_died: str = "狼人已经团灭了, 好人阵营获胜"
    werewolves_kill_all: str = "狼人已经消灭了所有的好人, 狼人胜利"
    werewolves_overwhelm: str = "狼人阵营已经占据了绝对优势, 狼人胜利"

    night_start: str = "夜晚降临了..."
    night_is_over: str = "夜晚结束了..."

    statements_are_given: str = "所有人发言完毕, 进入投票环节..."
    votes_are_given: str = "所有人投票完毕..."

    vote_is_draw: str = "没有人被投票处决..."
    kill_by_votes: str = "{killed}得票最高, 被处决了..."

    def desc_new_dawn(
            self,
            date: int,
            players: List[str],
            scene: str,
    ) -> str:
        """
        描述新的一个黎明.
        """
        pass


class Prompts(BaseModel):
    pass


class WerewolfGameConfig(BaseModel):
    think: str = Field(
        description="游戏会有多种配置, 每种配置可以实装为一个 think, 用来驱动一个游戏",
    )

    roles: List[RoleInfo] = Field(
        description="游戏设定好的角色和设置."
    )

    players: List[Player] = Field(
        description="默认的玩家的设定. 玩家的角色可以留空",
    )

    debug: bool = Field(
        description="是否开启 debug 模式",
        default=True,
    )

    llm_config: str = Field(
        description="选定的 llm 配置 id",
        default="gpt-4-0613",
    )

    prompts: Prompts = Field(
        description="设定好的 prompts",
        default_factory=Prompts,
    )

    speech: SpeechCraft = Field(
        default_factory=SpeechCraft,
    )
