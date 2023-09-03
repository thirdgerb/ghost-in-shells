from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, ClassVar, Optional

from ghoshell.ghost import *
from ghoshell.llms.openai_contracts import OpenAIChatCompletion, OpenAIChatMsg
from ghoshell.prototypes.playground._werewolf.configs import WerewolfGameConfig, Role
from ghoshell.prototypes.playground._werewolf.thought import Day, Player, Night
from ghoshell.prototypes.playground._werewolf.thought import WerewolfGameThought, GameResult


class AbsWerewolfGameStage(Stage, ABC):
    """
    狼人杀游戏状态的基础类. 状态设计:

    - game start: 游戏开始
    - introduce: 角色之间互相介绍
    - twilight: 黄昏, 检查胜负.
    - night action: 进入夜晚
        - seer
        - witch
        - werewolf
    - dawn: 黎明, 检查胜负与生死.
    - discuss: 各自发言
    - votes: 各自投票
    - execute: 处决环节.
    - twilight: 继续进入黄昏. 循环.
    - game over: 游戏结束.
    """

    stage_name: ClassVar[str]

    def __init__(
            self,
            config: WerewolfGameConfig,
    ):
        self._config = config

    def url(self) -> URL:
        return URL.new(self._config.think, self.stage_name)

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return []

    def reactions(self) -> Dict[str, Reaction]:
        return {}

    def on_event(self, ctx: "Context", this: WerewolfGameThought, event: Event) -> Operator | None:
        if isinstance(event, OnActivating):
            return self.on_activate(ctx, this)
        elif isinstance(event, OnReceived):
            return self.on_received(ctx, this)
        return None

    def on_activate(self, ctx: "Context", this: WerewolfGameThought) -> Operator | None:
        """
        启动状态.
        """
        op = self._do_activate(ctx, this)
        if op is None:
            # 默认是等待用户输入, 输入就跳转 _next_stage
            return ctx.mind(this).awaits()
        return op

    @abstractmethod
    def _do_activate(self, ctx: "Context", this: WerewolfGameThought) -> Operator | None:
        """
        启动状态.
        """
        pass

    @abstractmethod
    def _next_stage(self, ctx: "Context", this: WerewolfGameThought) -> str:
        pass

    def on_received(self, ctx: "Context", this: WerewolfGameThought) -> Operator | None:
        """
        收到消息, 跳到下一个状态位.
        默认狼人杀全部都是 AI 进行的.
        玩家只能旁观, 第一期不做参与.
        """
        next_stage = self._next_stage(ctx, this)
        return ctx.mind(this).forward(next_stage)

    @classmethod
    def _llm(cls, ctx: "Context") -> OpenAIChatCompletion:
        return ctx.container.force_fetch(OpenAIChatCompletion)

    def _count_werewolves(self, survivors: List[str]) -> int:
        """
        计算剩余狼人的数量.
        """
        count = 0
        s = set(survivors)
        for player in self._config.players:
            if player.name in s and player.role == Role.WEREWOLF:
                count += 1
        return count

    def _is_game_finish(self, survivors: List[str]) -> Optional[str]:
        """
        简单判断游戏的状态. 如果结束了返回一句话描述.
        """
        live = len(survivors)
        werewolves = self._count_werewolves(survivors)
        if werewolves == 0:
            # 狼人死光
            return self._config.speech.werewolves_died
        elif werewolves == live:
            # 只剩下狼人.
            return self._config.speech.werewolves_kill_all
        elif werewolves * 2 >= live:
            return self._config.speech.werewolves_overwhelm
        return None

    def _prompt(self, ctx: "Context", this: WerewolfGameThought, prompt: str) -> str:
        """
        运行一个 prompt.
        """
        llm = self._llm(ctx)
        choice = llm.chat_completion(
            session_id=ctx.input.trace.session_id,
            chat_context=[
                OpenAIChatMsg(
                    role=OpenAIChatMsg.ROLE_SYSTEM,
                    content=prompt,
                )
            ],
            config_name=self._config.llm_config,
        )
        value = choice.get_content()
        # debug 模式发送给用户
        if self._config.debug:
            ctx.send_at(this).markdown(
                f"# prompt \n\n{prompt}"
            )
            ctx.send_at(this).markdown(
                f"# debug \n\n{choice.model_dump_json(indent=2)}"
            )
        # 如果拿到了空值.
        if not value:
            raise LogicError("prompt got empty value")
        return value

    @classmethod
    def _say(cls, ctx: "Context", this: WerewolfGameThought, text: str) -> None:
        ctx.send_at(this).markdown(text)
        this.data.events.append(text)

    _players: Optional[Dict] = None

    @property
    def _player_map(self) -> Dict[str, Player]:
        if self._players is None:
            players = {}
            for p in self._config.players:
                players[p.name] = p
            self._players = players
        return self._players

    def _get_player_memory(self, this: WerewolfGameThought, name: str) -> str:
        """
        描述用户视角的记忆.
        """
        pass


class GameStartStage(AbsWerewolfGameStage):
    """
    游戏开始.
    """


class GameIntroduceStage(AbsWerewolfGameStage):
    """
    游戏场景, 每个人进行自我介绍.
    """


class GameOverStage(AbsWerewolfGameStage):
    """
    游戏结束.
    """
    pass


class DawnStage(AbsWerewolfGameStage):
    """
    黎明回合. 判断下是否已经分出胜负了.
    """

    stage_name = "dawn"

    def _do_activate(self, ctx: "Context", this: WerewolfGameThought) -> Operator | None:
        yesterday = this.data.current_day
        if yesterday is None:
            raise LogicError(f"dawn stage meet empty date")
        survivors = yesterday.night.survivors

        # 新的一天开始了.
        self._dawn_start(ctx, this, yesterday)

        # 判定游戏胜负.
        finish = self._is_game_finish(survivors)
        if finish is not None:
            result = GameResult(
                description=finish,
                survivors=survivors.copy(),
            )
            this.data.result = result
            # 游戏结算.
            return ctx.mind(this).forward(GameOverStage.stage_name)
        # 白天开始.
        return None

    def _dawn_start(self, ctx: "Context", this: WerewolfGameThought, day: Day) -> None:
        # 让 llm 写一段话描述这个夜晚.
        prompt = day.night.night_description_prompt(self._config.prompts)
        scene = self._prompt(ctx, this, prompt)

        # 生成新的一天.
        new_day = Day(
            round=day.round + 1,
            daytime=dict(
                players=day.night.survivors.copy(),
                scene=scene,
            ),
        )
        this.data.days.append(this.data.current_day)
        this.data.current_day = new_day

        # 告知用户发生了什么.
        description = self._config.speech.desc_new_dawn(
            date=new_day.round,
            players=new_day.daytime.players,
            scene=scene,
        )
        self._say(ctx, this, description)
        return None

    def _next_stage(self, ctx: "Context", this: WerewolfGameThought) -> str:
        # 进入讨论环节.
        return DiscussStage.stage_name


class TwilightStage(AbsWerewolfGameStage):
    """
    黄昏回合, 判断下是否已经分出胜负了.
    """
    stage_name = "twilight"

    def _do_activate(self, ctx: "Context", this: WerewolfGameThought) -> Operator | None:
        day = this.data.current_day
        if day is None:
            raise LogicError(f"dawn stage meet empty date")
        day = day
        night = day.night
        # 初始化夜晚.
        if night is None:
            day.night = night = self._execute_by_votes(ctx, this, day)
        survivors = night.survivors
        # 判定游戏胜负.
        finish = self._is_game_finish(survivors)
        if finish is not None:
            result = GameResult(
                description=finish,
                survivors=survivors.copy(),
            )
            this.data.result = result
            # 游戏结算.
            return ctx.mind(this).forward(GameOverStage.stage_name)
        return self._night_start(ctx, this, day)

    def _execute_by_votes(self, ctx: "Context", this: WerewolfGameThought, day: Day) -> Night:
        daytime = day.daytime
        survivors = daytime.players

        # 计票环节.
        votes = daytime.votes
        vote_counts = {}
        for voter in votes:
            target = votes[voter]
            if target not in vote_counts:
                vote_counts[target] = 0
            vote_counts[target] = vote_counts[target] + 1

        # 查看排名第一.
        first = []
        first_count = 0
        for target in vote_counts:
            count = vote_counts[target]
            if count < first_count:
                # 逃过一死.
                continue
            elif count == first_count:
                first.append(target)
            else:
                first = [target]

        if len(first) != 1:
            self._say(ctx, this, self._config.speech.vote_is_draw)
            return Night(
                players=survivors.copy(),
                survivors=survivors.copy(),
            )
        else:
            killed = first[0]
            # 告知用户.
            msg = self._config.speech.kill_by_votes.format(killed=killed)
            self._say(ctx, this, msg)
            # 生成新的晚上.
            new_survivors = []
            for s in survivors:
                if s == killed:
                    continue
                new_survivors.append(s)
            return Night(
                players=new_survivors.copy(),
                survivors=new_survivors.copy(),
            )

    def _night_start(self, ctx: "Context", this: WerewolfGameThought, day: Day) -> Operator | None:
        day.night = day.daytime.new_night()
        # 说话, 记录发生的事情.
        self._say(ctx, this, self._config.speech.night_start)
        return None

    def _next_stage(self, ctx: "Context", this: WerewolfGameThought) -> str:
        # 进入讨论环节.
        return NightActionStage.stage_name


class NightActionStage(AbsWerewolfGameStage):
    """
    夜间行动回合.
    """
    stage_name = "night_action"

    def _do_activate(self, ctx: "Context", this: WerewolfGameThought) -> Operator | None:
        night = this.data.current_day.night
        if night is None:
            raise LogicError("night shall not be none")
        # 检查每个人的可能的动作. 只检查 survivors. 因为可能有人已经死了.
        for survivor in night.survivors:
            player = self._player_map.get(survivor, None)
            if player is None:
                raise LogicError(f"survivor {survivor} is not exists in config")
            if player.role not in Role.HAS_ABILITIES:
                # 没有平民什么事情.
                continue
            if player.name in night.actions:
                # 如果这个人已经做过动作了.
                continue
            night.actor = player.name
            # 进入角色的回合.
            return ctx.mind(this).forward(player.role)
        # 所有动作都做完了, 等待进入黎明.
        self._say(ctx, this, self._config.speech.night_is_over)
        return None

    def _next_stage(self, ctx: "Context", this: WerewolfGameThought) -> str:
        # 等待用户输入, 进入黎明.
        return DawnStage.stage_name


class SeerNightStage(AbsWerewolfGameStage):
    """
    先知的夜晚回合
    """
    stage_name = Role.SEER


class WerewolfNightStage(AbsWerewolfGameStage):
    """
    狼人的夜晚回合
    """
    stage_name = Role.WEREWOLF


class WitchNightStage(AbsWerewolfGameStage):
    """
    女巫的夜晚回合.
    """
    stage_name = Role.WITCH


class DiscussStage(AbsWerewolfGameStage):
    """
    讨论环节
    """
    stage_name = "discuss"

    def _do_activate(self, ctx: "Context", this: WerewolfGameThought) -> Operator | None:
        daytime = this.data.current_day.daytime
        for s in daytime.players:
            if s in daytime.statements:
                # 已经发言过了.
                continue
            # 让 AI 玩家发表观点.
            self._give_statement(ctx, this, s)
            # 等待用户输入进入下一步.
            return None
        # 全部发言过了. 进入投票环节.
        self._say(ctx, this, self._config.speech.statements_are_given)
        # 进入投票环节.
        return ctx.mind(this).forward(VoteStage.stage_name)

    def _give_statement(self, ctx: "Context", this: WerewolfGameThought, player: str) -> None:
        pass

    def _next_stage(self, ctx: "Context", this: WerewolfGameThought) -> str:
        # 重复自己.
        return self.stage_name


class VoteStage(AbsWerewolfGameStage):
    """
    轮流投票的环节.
    """
    stage_name = "vote"

    def _do_activate(self, ctx: "Context", this: WerewolfGameThought) -> Operator | None:
        daytime = this.data.current_day.daytime
        for s in daytime.players:
            if s in daytime.votes:
                # 已经投票过了.
                continue
            # 让 AI 玩家投票.
            self._vote(ctx, this, s)
            # 等待用户输入进入下一步.
            return None
        # 全部节投票完了. 进行计票.
        self._say(ctx, this, self._config.speech.votes_are_given)
        # 进入黄昏.
        return ctx.mind(this).forward(TwilightStage.stage_name)

    def _vote(self, ctx: "Context", this: WerewolfGameThought, player: str) -> None:
        prompt = self._vote_prompt(this, player)
        value = self._prompt(ctx, this, prompt)

    def _vote_prompt(self, this: WerewolfGameThought, player: str) -> str:
        pass

    def _next_stage(self, ctx: "Context", this: WerewolfGameThought) -> str:
        # 重复自身.
        return self.stage_name
