import time
from abc import ABCMeta, abstractmethod
from random import randint
from typing import Optional, List, Dict, Any, ClassVar, Tuple

import yaml
from pydantic import BaseModel, Field

from ghoshell.framework.reactions import CommandReaction, Command, CommandOutput
from ghoshell.ghost import *
from ghoshell.llms.utils import fetch_ctx_prompter
from ghoshell.messages import *


# ----- Thought ----- #


class _RoundInfo(BaseModel):
    """
    轮次里的基本信息.
    """
    # 第几轮.
    round: int

    # 玩家的描述词
    commits: Dict[str, str] = Field(default_factory=dict)

    # 玩家的投票结果
    votes: Dict[str, str] = Field(default_factory=dict)

    # 每个活跃玩家这一轮的思考内容.
    # 会带到下一轮游戏中, 作为他的思考上下文.
    player_thoughts: Dict[str, str] = Field(default_factory=dict)

    # 结果描述
    result: str = ""

    # 当前发言的用户
    current_player: str = ""

    def vote_count(self, voted: str) -> int:
        """
        计票. 写快点.
        """
        vote_count = 0
        for player in self.votes.values():
            if voted == player:
                vote_count += 1
        return vote_count

    def round_votes_text(self, players: List[str]) -> str:
        """
        每个回合所有用户的投票.
        """
        return self.__join_ordered_player_dict(players, self.votes)

    def round_commits_text(self, players: List[str]) -> str:
        """
        每个回合所有用户提交的描述.
        """
        return self.__join_ordered_player_dict(players, self.commits)

    @classmethod
    def __join_ordered_player_dict(cls, players: List[str], mapping: Dict) -> str:
        if not mapping:
            return ""

        temp = "- {player}: {value}"

        result = []
        for player in players:
            if player in mapping:
                value = mapping[player]
                line = temp.format(player=player, value=value)
                result.append(line)
        return "\n".join(result)


class _Gaming(BaseModel):
    """
    游戏的当前状态.
    """
    # 游戏的轮次
    round: int = 0

    # 对词的基本描述
    word_desc: str = "一种面食"

    user_player: str = ""

    # 玩家的词
    player_word: str = "饺子"

    # 卧底的词
    undercover_word: str = "包子"

    # 卧底的身份
    undercover: List[str] = Field(default_factory=list)

    # 是否是 debug 模式.
    debug_mode: bool = False

    # 出局的人
    exiled: List[str] = Field(default_factory=list)

    # 游戏每一轮的信息.
    rounds: List[_RoundInfo] = Field(default_factory=list)

    # 每个玩家游戏结束时的感想.
    feelings: Dict[str, str] = Field(default_factory=dict)

    def someones_word(self, someone: str) -> str:
        return self.undercover_word if someone in set(self.undercover) else self.player_word


class _UndercoverGameInfo(BaseModel):
    """
    谁是卧底游戏的核心思维.
    """
    # 参与的玩家名字. 用来做 key
    players: List[str] = Field(default_factory=lambda: ["丁一", "牛二", "张三", "李四", "王五", "赵六"])

    # 是否已经向玩家介绍过游戏
    instructed: bool = False

    # 游戏自身的状态.
    gaming: _Gaming = Field(default_factory=_Gaming)

    def current_players(self) -> List[str]:
        exiled = set(self.gaming.exiled)
        result = []
        for p in self.players:
            if p in exiled:
                continue
            result.append(p)
        return result


class UndercoverGameThought(Thought):
    # 游戏退出时不遗忘, 保持状态.
    priority = 0.1

    def __init__(self, args: Dict):
        self.game_info = _UndercoverGameInfo()
        super().__init__(args)

    def prepare(self, args: Dict) -> None:
        return None

    def set_variables(self, variables: Dict) -> None:
        self.game_info = _UndercoverGameInfo(**variables)

    def vars(self) -> Dict | None:
        _vars = self.game_info.model_dump()
        return _vars

    def _destroy(self) -> None:
        del self.game_info


# ----- think driver ----- #

class UndercoverGameDriver(ThinkDriver):
    """
    偷懒的实现, 怎么快怎么来.
    有时间的话改成一个可配置的游戏.
    """

    PLAYER_ROLE: ClassVar[str] = "普通玩家"
    UNDERCOVER_ROLE: ClassVar[str] = "卧底"

    WATCH_AI_ONLY: ClassVar[str] = """
您没有扮演任何角色, 请观看 AI 的演出. 
"""

    WELCOMING: ClassVar[str] = """
# LLM playing Undercover Game Demo

你好!

这是一个 "谁是卧底" 的小游戏. 主要目的是测试 AI 的思维能力, 以及验证 Ghoshell 框架的一些基本特性.  

游戏进行中, 您可以随时通过 /help 查看可用的指令. 
比如:
- /rule : 查询游戏的基本规则
- /debug : 开启 debug 模式
- /restart : 重启游戏. 
- /cancel : 退出.

输入其它任意信息, 游戏开始. 
"""

    GAME_RULE: ClassVar[str] = """

游戏的规则如下: 

- 一共有六名玩家参与, 你可以选择是否扮演其中一名, 其它的角色由 AI 扮演.
- 玩家会分为两组, 一组是 "普通玩家", 一组是 "卧底", 相互对立, 玩家互相之间都不知道身份
- 游戏会给出两个意思相近的名词, 指的是两个事物. 普通玩家分到一个, 卧底分到另一个
- 游戏的目标是, 通过多次对话和投票, 将对立分组的玩家投票出局.
    - 普通玩家: 尽可能找出谁是卧底, 然后在投票环节集中将卧底投出去. 尽可能让票数集中.
    - 卧底: 尽可能隐藏自己卧底身份, 将票数集中在普通玩家身上. 
- 游戏的胜负判定:
    - 普通玩家胜利: 所有的卧底都被投票清除时, 玩家胜利.  
    - 卧底胜利: 只剩下三名玩家时, 如果有任何一个卧底在其中, 则卧底方胜利.  
- 游戏开始后会逐轮进行, 每一轮分为两个环节.
    - 第一个环节是 "描述环节", 每个玩家需要用一句话描述自己得到的这个名词, 注意:
        - 不能说出词本身
        - 不要说与名词对应事物无关的内容
        - 尽可能暗示自己是 "普通玩家" 的身份
    - 第二个环节是 "投票环节", 每个玩家需要投票选出一个出局的对象. 注意:
        - 通常不会投自己
        - 尽量让票数集中
        - 得票最高的玩家将会被出局. 
        - 得票数相同的话, 系统随机挑选一人出局. 
"""

    PLAYER_PRIVATE_INFORMATION_TEMP: ClassVar[str] = """
- 游戏玩家: {players}
- 你的名字是: {name}
- 你的身份是: {role}
- 游戏的名词简介是: {desc}
- 你拿到的名词是: {word}
"""
    GAME_PRIVATE_INFORMATION_TEMP: ClassVar[str] = """
- 游戏玩家: {players}
- 卧底: {undercover}
- 游戏的名词简介是: {word_desc}
- 普通玩家拿到的词: {player_word}
- 卧底玩家拿到的词: {undercover_word}
"""
    ASK_CONTINUE: ClassVar[str] = """
(输入任何信息继续)
"""

    LET_START: ClassVar[str] = """
让我们开始游戏吧!
"""

    DESCRIBE_TEMP: ClassVar[str] = """
玩家 {name} 说: {description}
"""

    ROUND_VOTES_TEMP: ClassVar[str] = """
本轮游戏投票如下:

{votes}
"""

    ROUND_RESULT_TEMP: ClassVar[str] = """
系统判定: {result}
"""

    GAME_RESULT_TEMP: ClassVar[str] = """
游戏结束!

- 游戏轮次: {round}
- 普通玩家阵营: {players}
- 卧底阵营: {undercover}
- 最后存活玩家: {alive}

恭喜{winner}方获得最后的胜利!

大家的感想是:

{feelings}


游戏数据保存在 {filename}

(输入任何内容结束)
"""

    GAME_DESC: ClassVar[str] = """
简述规则: 

六个玩家分成两组, 一组是 "普通玩家" 4个人, 一组是 "卧底" 2 个人, 相互之间都不知道身份.

游戏会给每一组玩家分配一个 "关键词", "普通玩家" 拿到的词和 "卧底" 有相同点也有不同点. 互相不知道别人拿到的 "关键词" 是什么.

游戏开始后, 每一轮有两个环节:
- "描述环节": 每个玩家需要用一个形容词描述自己拿到的 关键词, 不能雷同, 不能包含 关键词 本身, 包括它的每个字.
- "投票环节": 每个玩家选出一个在场的玩家投票, 得票最高的玩家被淘汰, 然后进入下一轮.

胜负规则:
- 如果所有卧底都被投票淘汰, 则普通玩家获胜
- 如果只剩三个玩家, 中间包含任何一个卧底, 则卧底获胜. 

只能用中文回复. 
"""

    COMMIT_PROMPT_TEMP: ClassVar[str] = """
我在玩一局 "谁是卧底" 的小游戏. 

{game_desc}

---

我这局游戏的基本信息如下:

{private_info}

--- 

游戏进行过程的信息如下: 

{game_process}

    
现在轮到我发言了, 我需要回顾的规则是:

- 我的描述决不能包含我拿到的关键词本身
- 我的描述也不能偏离拿到的关键词
- 描述必须简单精辟, 最好只有一个形容词
- 我的描述绝对不能和别人说过的描述重复, 最好每个字都不同. 

我发言需要思考的策略是: 
{strategy}

我对 {my_word} 的特征的描述是:  
"""
    COMMIT_UNDERCOVER_STRATEGY: ClassVar[str] = """
- 普通玩家的词可能是什么?
- 作为卧底玩家, 我的描述需要尽可能接近普通玩家, 但绝对不能偏离自己拿到的关键词的特征.
- 我的描述也要避免普通玩家猜到我的关键词
- 我的描述绝不能和别人的描述相同
"""

    COMMIT_PLAYER_STRATEGY: ClassVar[str] = """
- 作为普通玩家, 我需要通过描述, 暗示其他普通玩家我是朋友
- 我得思考卧底玩家拿到的关键词是什么
- 我的描述, 得避免卧底玩家猜到我的关键词是什么
- 我的描述绝不能和别人的描述相同
"""

    EXILED_FEELING_PROMPT_TEMP: ClassVar[str] = """
我在玩一局 "谁是卧底" 的小游戏. 

{game_desc}

---

这局游戏的基本信息如下:

{game_info}

--- 

游戏进行过程的信息如下: 

{game_process}

现在我被淘汰了.

我当前的感想是:  
"""

    GAME_OVER_PROMPT_TEMP: ClassVar[str] = """
我在玩一局 "谁是卧底" 的小游戏. 

{game_desc}

---

我这局游戏的基本信息如下:

{private_info}

--- 

游戏进行过程的信息如下: 

{game_process}

---
游戏结束!

这局游戏的设定揭晓:

{game_info}

获胜方是: {winner}

我当前的感想是:  
"""

    VOTE_PROMPT_TEMP: ClassVar[str] = """
我在玩一局 "谁是卧底" 的小游戏. 

{game_desc}

---

我这局游戏的基本信息如下:

{private_info}

--- 

游戏进行过程的信息如下: 

{game_process}

现在轮到我投票了, 我需要回顾的规则是:
- 当前可投票对象是: {alive}
- 得票最高的人, 会从游戏里淘汰掉.
- 如果投票结果分不出最高票, 系统会随机淘汰掉一人. 

我需要逐步思考的投票策略是:

{strategy}

然后我要把思考结果按 yaml 的 dict 输出, 举例:

```yaml
vote: 名字
reason: 原因
```

思考结果是:
"""
    UNDERCOVER_VOTE_STRATEGY: ClassVar[str] = """
- 我是卧底. 
- 得票最高的玩家会被淘汰, 被人投票是坏事
- 我想要卧底阵营获胜, 所以我需要投票淘汰普通玩家 
- 我拿到的关键词是 "{my_word}"
- 普通玩家的关键词也符合 "{word_desc}"
- 如果得票高的可能是普通玩家, 我应该投给他
- 如果得票高的可能是卧底, 我应该投给第二高的人, 以分散票数

基于策略, 我需要思考: 应该投票给谁? 他的发言是什么? 我为何投票给他? 普通玩家的关键词可能是什么?
"""

    PLAYER_VOTE_STRATEGY: ClassVar[str] = """
- 我是普通玩家.
- 我想要普通玩家阵营获胜, 就要尽可能投票给卧底
- 我拿到的词是 "{my_word}", 谁给出描述不符合它的特性, 就可能是卧底.
- 卧底很可能投票给普通玩家. 
- 我需要投票给卧底, 而且票数要集中, 确保卧底能被投出去.

基于策略, 我需要思考: 谁是卧底呢? 他的发言是什么? 我为何投票给他? 卧底的关键词可能是什么?
"""

    ASK_WHAT_WORD_LIKE: ClassVar[str] = """
请问这次游戏给的提示词大概是什么类型 (会告诉每一个玩家)?
"""
    ASK_PLAYER_WORD: ClassVar[str] = """
请问普通玩家拿到的词是什么?
"""

    ASK_UNDERCOVER_WORD: ClassVar[str] = """
请问卧底玩家拿到的词是什么?
"""

    ASK_DO_USER_WANT_JOIN_TEMP: ClassVar[str] = """
游戏目前的参与角色有: {names}

请问您想加入游戏吗? 

回复任意角色名, 您将扮演该角色. 输入其它任意信息, 游戏开始. 
"""

    UNSUPPORTED_MESSAGE: ClassVar[str] = """
对不起, 当前游戏不支持文本以外的消息!
"""

    UNSUPPORTED_EMPTY_TEXT: ClassVar[str] = """
对不起, 无法处理空的消息
"""

    ROUND_START_TEMP: ClassVar[str] = """
第 {round} 轮游戏开始:
"""

    ROUND_ALL_COMMITS_TEMP: ClassVar[str] = """
当前的发言结果是:

{commits}
"""

    ROUND_THOUGHT_TEMP: ClassVar[str] = """
我这一轮的思考是:

{thought}
"""

    AI_COMMIT_DESC_TEMP: ClassVar[str] = """
请用户 {player} 发言:
"""

    AI_COMMIT_VOTE_TEMP: ClassVar[str] = """
请用户 {player} 进行投票:
"""

    ASK_USER_TO_COMMIT_DESC_TEMP: ClassVar[str] = """
请您作为用户 {player} 发言:
"""
    ASK_USER_TO_VOTE_TEMP: ClassVar[str] = """
请您作为用户 {player} 投票:
"""

    PLAYER_SPEAK_OUT_VOTE_TEMP: ClassVar[str] = """
用户 {player} 投票给: {vote}

{vote} 现在得票是: {tickets}    
"""

    PLAYER_SPEAK_OUT_DESCRIBE_TEMP: ClassVar[str] = """
用户 {player} 说的是:

{content}
"""

    VOTE_TARGET_NOT_EXISTS_TEMP: ClassVar[str] = """
投票对象 {content} 不存在!! 投票作废. 
"""

    def __init__(
            self,
            # 保存 review 的地址.
            review_dir: str,
            think_name: str | None = None,
    ):
        self.review_dir = review_dir
        if think_name is None:
            think_name = "game/undercover"
        self.think_name = think_name

    @classmethod
    def driver_name(cls) -> str:
        return cls.__name__

    def from_meta(self, meta: ThinkMeta) -> "Think":
        return UndercoverGameDemoThink(self)

    def review_saving_filename(self) -> str:
        """
        复盘数据保存的路径.
        """
        now = time.strftime("%Y_%m_%d_%H_%M_%S")
        filename = f"{self.review_dir.rstrip('/')}/{now}.yaml"
        return filename

    def to_meta(self) -> ThinkMeta:
        return ThinkMeta(
            id=self.think_name,
            kind=self.driver_name(),
        )

    @classmethod
    def save_review_result(cls, filename: str, game_info: _UndercoverGameInfo) -> None:
        config = game_info.model_dump()
        with open(filename, 'w') as f:
            yaml.dump(config, f, allow_unicode=True)


# ----- think ----- #

class UndercoverGameDemoThink(Think):
    """
    实现一个 "谁是卧底" 的小游戏
    用来验证:
    1. 可编程的复杂多轮对话
    2. 极简的内省的思维过程
    3. 引擎的单任务调度能力
    4. AI 的模型能力.

    要求:
    1. AI 扮演 谁是卧底 里的玩家.
    2. 玩家也可以参与扮演, 也可以不参与.
    3. 玩家来选择谁是卧底的关键词.
    4. 游戏过程中有角色的内部思考.
    5. 游戏结束可以复盘.
    6. 游戏结束后, 完整的对话过程可以存档保留.

    关于可配置化的问题, 可以先偷懒, 用一个基准模板完成所有的逻辑.
    未来再加入可配置化.
    """

    def __init__(
            self,
            driver: UndercoverGameDriver
    ):
        self.driver = driver

    def url(self) -> URL:
        return URL.new_think(self.driver.think_name)

    def to_meta(self) -> ThinkMeta:
        return self.driver.to_meta()

    def desc(self, ctx: Context, thought: Thought) -> Any:
        """
        描述未来会用到机器人里, 让机器人可以识别各种任务.
        """
        return """
这是一个 "谁是卧底" 的小游戏. 
"""

    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        """
        生成一个会话唯一的 id
        """
        return self.url().new_id(extra=ctx.input.trace.model_dump(include={"session_id"}))

    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        return UndercoverGameThought(args)

    def result(self, ctx: Context, this: Thought) -> Optional[Dict]:
        """
        暂时不返回结果. 有必要可以返回一个复盘文档.
        """
        return None

    def all_stages(self) -> List[str]:
        keys = self._stages().keys()
        return list(sorted(keys))

    __stages = None

    def _stages(self) -> Dict[str, Stage]:
        # todo
        if self.__stages is None:
            self.__stages = {
                _DefaultStage.stage_name: _DefaultStage(self.driver),
                _InitializeStage.stage_name: _InitializeStage(self.driver),
                _RoundCommitStage.stage_name: _RoundCommitStage(self.driver),
                _RoundInitializeStage.stage_name: _RoundInitializeStage(self.driver),
                _RoundVoteStage.stage_name: _RoundVoteStage(self.driver),
                _AskUserIfJoinStage.stage_name: _AskUserIfJoinStage(self.driver),
                _AskUserWhatUndercoverWord.stage_name: _AskUserWhatUndercoverWord(self.driver),
                _AskUserWhatPlayerWord.stage_name: _AskUserWhatPlayerWord(self.driver),
                _AskUserWhatWordObjectLike.stage_name: _AskUserWhatWordObjectLike(self.driver),
                _VoteResultStage.stage_name: _VoteResultStage(self.driver),
                _GameResultStage.stage_name: _GameResultStage(self.driver),
            }
        return self.__stages

    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        return self._stages().get(stage_name, None)


# ----- stages ----- #

class _AbsStage(Stage, metaclass=ABCMeta):
    stage_name: ClassVar[str] = ""

    def __init__(self, driver: UndercoverGameDriver):
        self.driver = driver

    def url(self) -> URL:
        return URL(think=self.driver.think_name, stage=self.stage_name)

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {
            "/rule": ShowRuleCmdReaction(),
            "/debug": DebugCmdReaction(),
        }

    def on_event(self, ctx: "Context", this: UndercoverGameThought, event: Event) -> Operator | None:
        if isinstance(event, OnActivating):
            return self.on_activate(ctx, this)
        if isinstance(event, OnReceived):
            return self.on_received(ctx, this)
        if isinstance(event, OnPreempted):
            return self.on_preempted(ctx, this)
        return None

    @abstractmethod
    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        pass

    @abstractmethod
    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        pass

    def on_preempted(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        # 偷懒不写模板了.
        ctx.send_at(this).text("欢迎回到 谁是卧底小游戏!  让我们恢复之前的进程. ")
        return ctx.mind(this).repeat()

    @classmethod
    def _receive_valid_text_message(
            cls,
            ctx: "Context",
            this: UndercoverGameThought,
            allow_empty: bool = False
    ) -> Tuple[str, Operator | None]:
        text = ctx.read(Text)
        if text is None:
            # 无法处理的消息.
            ctx.send_at(this).err(UndercoverGameDriver.UNSUPPORTED_MESSAGE)
            return "", ctx.mind(this).repeat()

        content = text.content.strip()
        if not allow_empty and not content:
            # 无法处理的消息.
            ctx.send_at(this).err(UndercoverGameDriver.UNSUPPORTED_EMPTY_TEXT)
            return content, ctx.mind(this).repeat()
        return content, None

    @classmethod
    def _current_round_info(
            cls,
            this: UndercoverGameThought,
    ) -> _RoundInfo:
        current_round = this.game_info.gaming.round
        round_info = this.game_info.gaming.rounds[current_round]
        return round_info

    @classmethod
    def _user_private_info(
            cls,
            this: UndercoverGameThought,
            name: str,
    ):
        players = this.game_info.players
        role = UndercoverGameDriver.PLAYER_ROLE
        word = this.game_info.gaming.player_word
        if name in this.game_info.gaming.undercover:
            role = UndercoverGameDriver.UNDERCOVER_ROLE
            word = this.game_info.gaming.undercover_word

        text = UndercoverGameDriver.PLAYER_PRIVATE_INFORMATION_TEMP.format(
            players=", ".join(players),
            name=name,
            role=role,
            desc=this.game_info.gaming.word_desc,
            word=word,
        )
        return text

    @classmethod
    def _game_private_info(
            cls,
            this: UndercoverGameThought,
    ):
        players = this.game_info.players
        undercover = this.game_info.gaming.undercover

        text = UndercoverGameDriver.GAME_PRIVATE_INFORMATION_TEMP.format(
            players=", ".join(players),
            undercover=", ".join(undercover),
            word_desc=this.game_info.gaming.word_desc,
            player_word=this.game_info.gaming.player_word,
            undercover_word=this.game_info.gaming.undercover_word,
        )
        return text

    def _game_exiled_feeling(self, ctx: Context, this: UndercoverGameThought, player: str) -> None:
        """
        比赛结束的想法.
        """
        game_info = self._game_private_info(this)
        game_process = self._game_process_for_player(this, player)

        prompt = UndercoverGameDriver.EXILED_FEELING_PROMPT_TEMP.format(
            game_desc=UndercoverGameDriver.GAME_DESC,
            game_info=game_info,
            game_process=game_process,
        )

        if this.game_info.gaming.debug_mode:
            # debug 模式会打印 prompt
            ctx.send_at(this).markdown("# debug mode: feeling prompt \n\n" + prompt)

        prompter = fetch_ctx_prompter(ctx)
        resp = prompter.text_completion(prompt)
        if this.game_info.gaming.debug_mode or not this.game_info.gaming.user_player:
            ctx.send_at(this).markdown(f"# player {player} exiled feeling \n\n" + resp)
        this.game_info.gaming.feelings[player] = resp
        return

    def _game_over_feeling(self, ctx: Context, this: UndercoverGameThought, player: str, winner: str) -> None:
        game_info = self._game_private_info(this)
        private_info = self._user_private_info(this, player)
        game_process = self._game_process_for_player(this, player)

        prompt = UndercoverGameDriver.GAME_OVER_PROMPT_TEMP.format(
            game_desc=UndercoverGameDriver.GAME_DESC,
            game_info=game_info,
            private_info=private_info,
            game_process=game_process,
            winner=winner,
        )

        if this.game_info.gaming.debug_mode:
            # debug 模式会打印 prompt
            ctx.send_at(this).markdown("# debug mode: feeling prompt \n\n" + prompt)

        prompter = fetch_ctx_prompter(ctx)
        resp = prompter.text_completion(prompt)
        this.game_info.gaming.feelings[player] = resp
        return

    @classmethod
    def _game_process_for_player(cls, this: UndercoverGameThought, player: str) -> str:
        game_process = []
        for round_info in this.game_info.gaming.rounds:
            round_process = cls._round_process_for_player(this, round_info, player)
            game_process.append(round_process)
        return "\n---\n\n".join(game_process)

    @classmethod
    def _round_process_for_player(cls, this: UndercoverGameThought, round_info: _RoundInfo, player: str) -> str:
        round_desc = []
        round_start = UndercoverGameDriver.ROUND_START_TEMP.format(round=round_info.round + 1)
        round_desc.append(round_start)

        if len(round_info.commits) > 0:
            commit_info = round_info.round_commits_text(this.game_info.players)
            round_commits = UndercoverGameDriver.ROUND_ALL_COMMITS_TEMP.format(commits=commit_info)
            round_desc.append(round_commits)

        if len(round_info.votes) > 0:
            vote_info = round_info.round_votes_text(this.game_info.players)
            round_vote = UndercoverGameDriver.ROUND_VOTES_TEMP.format(votes=vote_info)
            round_desc.append(round_vote)

        if player in round_info.player_thoughts:
            thought = round_info.player_thoughts[player]
            thought_text = UndercoverGameDriver.ROUND_THOUGHT_TEMP.format(thought=thought)
            round_desc.append(thought_text)

        if round_info.result:
            round_desc.append(round_info.result)

        return "\n\n".join(round_desc)

    def _ai_player_commit_describe(self, ctx: "Context", this: UndercoverGameThought, player: str) -> str:
        private_info = self._user_private_info(this, player)
        game_process = self._game_process_for_player(this, player)
        my_word = this.game_info.gaming.someones_word(player)
        strategy = UndercoverGameDriver.COMMIT_UNDERCOVER_STRATEGY if my_word == this.game_info.gaming.undercover_word \
            else UndercoverGameDriver.COMMIT_PLAYER_STRATEGY

        prompt = UndercoverGameDriver.COMMIT_PROMPT_TEMP.format(
            game_desc=UndercoverGameDriver.GAME_DESC,
            private_info=private_info,
            game_process=game_process,
            my_word=my_word,
            strategy=strategy,
        )

        if this.game_info.gaming.debug_mode:
            # debug 模式会打印 prompt
            ctx.send_at(this).markdown("# debug mode: prompt \n\n" + prompt)

        prompter = fetch_ctx_prompter(ctx)
        resp = prompter.text_completion(prompt)
        return resp

    def _ai_player_commit_vote(self, ctx: "Context", this: UndercoverGameThought, player: str) -> Tuple[str, str]:
        private_info = self._user_private_info(this, player)
        game_process = self._game_process_for_player(this, player)
        alive = this.game_info.current_players()
        my_word = this.game_info.gaming.someones_word(player)

        if player in set(this.game_info.gaming.undercover):
            my_role = UndercoverGameDriver.UNDERCOVER_ROLE
            strategy = UndercoverGameDriver.UNDERCOVER_VOTE_STRATEGY.format(
                my_word=my_word,
                word_desc=this.game_info.gaming.word_desc
            )
        else:
            my_role = UndercoverGameDriver.PLAYER_ROLE
            strategy = UndercoverGameDriver.PLAYER_VOTE_STRATEGY.format(my_word=my_word)

        prompt = UndercoverGameDriver.VOTE_PROMPT_TEMP.format(
            game_desc=UndercoverGameDriver.GAME_DESC,
            private_info=private_info,
            game_process=game_process,
            alive=", ".join(alive),
            my_role=my_role,
            strategy=strategy,
        )
        if this.game_info.gaming.debug_mode:
            # debug 模式会打印 prompt
            ctx.send_at(this).markdown("# debug mode: thought prompt \n\n" + prompt)

        prompter = fetch_ctx_prompter(ctx)
        resp = prompter.text_completion(prompt)

        if this.game_info.gaming.debug_mode or not this.game_info.gaming.user_player:
            # debug 模式会打印 prompt
            ctx.send_at(this).markdown("\n\n".join([
                "# debug mode: vote reason",
                private_info,
                resp,
            ]))

        if resp.startswith("```yaml"):
            resp = resp[7:]
        if resp.endswith("```"):
            resp = resp[:len(resp) - 3]
        if resp.startswith("```"):
            resp = resp[3:]

        loaded: Dict = yaml.safe_load(resp.strip())
        # 偷懒, 不写校验了.
        return loaded.get("vote", ""), loaded.get("reason", "")


class _DefaultStage(_AbsStage):
    """
    游戏启动的 Stage.
    只是做基本的说明介绍.
    """

    stage_name = ""

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        ctx.send_at(this).markdown(UndercoverGameDriver.WELCOMING)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        """
        简单测试一下 task 的路径规划.
        """
        return ctx.mind(this).forward(
            _AskUserWhatWordObjectLike.stage_name,
            _AskUserWhatPlayerWord.stage_name,
            _AskUserWhatUndercoverWord.stage_name,
            _AskUserIfJoinStage.stage_name,
            _InitializeStage.stage_name,
        )


class _InitializeStage(_AbsStage):
    """
    初始化一局游戏.
    需要初始化的内容:
    1. 玩家名字, 参与数量等: 固定的, 省得麻烦.
    2. 对话者是否要扮演一个角色, 扮演谁. 这是另一个 stage
    3. 游戏的主题词, 允许人工输入.
    4. 随机将一个主题词设置为卧底词.
    5. 随机分配玩家为 "普通" 或 "卧底"

    这些任务未完成可以跳转到完成该任务的 Stage.
    """
    stage_name: ClassVar[str] = "initialize"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        """
        游戏初始化要做的事情:
        1. 确定两个人做卧底.
        2. 咦, 好像没有 2 了.
        """
        length = len(this.game_info.players)
        undercover_1 = randint(0, length - 1)
        undercover_2 = randint(0, length - 2)
        if undercover_2 == undercover_1:
            undercover_2 += 1
        if undercover_2 >= length:
            undercover_2 = 0

        # 添加两个卧底.
        this.game_info.gaming.undercover.append(this.game_info.players[undercover_1])
        this.game_info.gaming.undercover.append(this.game_info.players[undercover_2])

        # 告诉用户它自己的身份.
        return self._inform_user(ctx, this)

    def _inform_user(self, ctx: "Context", this: UndercoverGameThought) -> Operator:
        user_player = this.game_info.gaming.user_player
        if user_player:
            # 偷偷告诉用户自己的信息.
            text = self._user_private_info(this, user_player)
            ctx.send_at(this).markdown(text)
        else:
            text = self._game_private_info(this)
            ctx.send_at(this).markdown(text)
            ctx.send_at(this).markdown(UndercoverGameDriver.WATCH_AI_ONLY)
        return ctx.mind(this).awaits()

    @classmethod
    def _let_start(cls, ctx: "Context", this: UndercoverGameThought) -> Operator:
        ctx.send_at(this).markdown(UndercoverGameDriver.LET_START)
        return ctx.mind(this).forward(_RoundInitializeStage.stage_name)

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        # 进入到游戏环节.
        return self._let_start(ctx, this)


class _AskUserWhatWordObjectLike(_AbsStage):
    """
    询问用户要测试的关键词是什么类型的.
    """

    stage_name: ClassVar[str] = "ask_what_the_word_is"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        ctx.send_at(this).text(UndercoverGameDriver.ASK_WHAT_WORD_LIKE)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        content, op = self._receive_valid_text_message(ctx, this)
        if op is not None:
            return op

        # 设置默认值.
        this.game_info.gaming.word_desc = content
        return ctx.mind(this).forward()


class _AskUserWhatPlayerWord(_AbsStage):
    """
    询问用户普通玩家拿到的词是什么.
    """
    stage_name = "ask_user_what_is_player_word"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        ctx.send_at(this).text(UndercoverGameDriver.ASK_PLAYER_WORD)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        content, op = self._receive_valid_text_message(ctx, this)
        if op is not None:
            return op

        # 设置默认值.
        this.game_info.gaming.player_word = content
        return ctx.mind(this).forward()


class _AskUserWhatUndercoverWord(_AbsStage):
    stage_name = "ask_user_what_is_undercover_word"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        ctx.send_at(this).text(UndercoverGameDriver.ASK_UNDERCOVER_WORD)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        content, op = self._receive_valid_text_message(ctx, this)
        if op is not None:
            return op

        this.game_info.gaming.undercover_word = content
        # 进入到初始化流程中.
        return ctx.mind(this).forward()


class _AskUserIfJoinStage(_AbsStage):
    """
    询问用户是否要加入游戏
    用户想要加入的话, 输入一个用户名.
    否则
    """

    stage_name = "ask_if_user_want_to_join_the_game"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        names = ", ".join(this.game_info.players)
        # 发送消息, 询问用户
        text = UndercoverGameDriver.ASK_DO_USER_WANT_JOIN_TEMP.format(names=names)
        ctx.send_at(this).text(text)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        content, op = self._receive_valid_text_message(ctx, this, allow_empty=True)
        if op is not None:
            return op

        # 用户回答是不是在用户名中?
        if content in set(this.game_info.players):
            ctx.send_at(this).text("ok")
            this.game_info.gaming.user_player = content

        # 进入初始化环节.
        return ctx.mind(this).forward()


class _RoundInitializeStage(_AbsStage):
    """
    介绍当前游戏轮次. 的内容.
    """

    stage_name: ClassVar[str] = "round_initialize"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        # 判定游戏是否已经结束
        if len(this.game_info.players) - len(this.game_info.gaming.exiled) <= 3:
            # 游戏已经接入, 进入结算环节.
            ctx.send_at(this).text("it looks game is over")
            return ctx.mind(this).awaits()

        # 有必要的话, 初始化 round
        current_round = this.game_info.gaming.round
        if current_round == len(this.game_info.gaming.rounds):
            new_round = _RoundInfo(round=current_round)
            this.game_info.gaming.rounds.append(new_round)

        text = UndercoverGameDriver.ROUND_START_TEMP.format(round=current_round + 1)
        ctx.send_at(this).markdown(text)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        """
        任何消息直接进入.
        """
        if len(this.game_info.players) - len(this.game_info.gaming.exiled) <= 3:
            # 游戏已经接入, 进入结算环节.
            return ctx.mind(this).forward(_GameResultStage.stage_name)
        return ctx.mind(this).forward(_RoundCommitStage.stage_name)


class _RoundCommitStage(_AbsStage):
    """
    活着的玩家逐一对自己的提示词进行描述.
    如果玩家是对话者, 则由对话者自行输入.
    """

    stage_name = "round_commit"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        # 重置当前说话的用户.
        round_info = self._current_round_info(this)
        round_info.current_player = ""
        exiled = set(this.game_info.gaming.exiled)
        for player in this.game_info.players:
            if player in exiled:
                # 已经淘汰的成员没有资格发言.
                continue
            # 用户已经发言过了.
            if player in round_info.commits:
                continue

            round_info.current_player = player
            # 轮到当前用户发言.
            if player == this.game_info.gaming.user_player:
                text = UndercoverGameDriver.ASK_USER_TO_COMMIT_DESC_TEMP.format(player=player)
            # 轮到 AI 用户发言.
            else:
                text = UndercoverGameDriver.AI_COMMIT_DESC_TEMP.format(player=player)
            # 发送消息.
            ctx.send_at(this).markdown(text)
            return ctx.mind(this).awaits()

        # 说明所有人发言已经结束了. 进入思考环节.
        commits = []
        for player in round_info.commits:
            commit = round_info.commits[player]
            commits.append(f"- {player} 发言是: {commit}")
        summary = UndercoverGameDriver.ROUND_ALL_COMMITS_TEMP.format(
            round=round_info.round,
            commits="\n".join(commits)
        )
        # 发送总结.
        ctx.send_at(this).markdown(summary)
        return ctx.mind(this).forward(_RoundVoteStage.stage_name)

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        # 获取当前用户.
        round_info = self._current_round_info(this)
        current_player = round_info.current_player
        if current_player == this.game_info.gaming.user_player:
            # 说明需要等待用户的回复.
            content, op = self._receive_valid_text_message(ctx, this, False)
            if op is None:
                return op
        else:
            # AI 发言环节.
            content = self._ai_player_commit_describe(ctx, this, current_player)

        # 设置好发言内容.
        round_info.commits[current_player] = content
        text = UndercoverGameDriver.PLAYER_SPEAK_OUT_DESCRIBE_TEMP.format(
            player=current_player,
            content=content,
        )
        ctx.send_at(this).markdown(text)
        # 重启当前环节.
        return ctx.mind(this).repeat()


class _RoundVoteStage(_AbsStage):
    """
    所有玩家逐一对本轮游戏进行思考, 得出自己的决策.
    并投票给某个人.
    """

    stage_name = "round_vote"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        # 重置当前说话的用户.
        round_info = self._current_round_info(this)
        round_info.current_player = ""
        exiled = set(this.game_info.gaming.exiled)
        for player in this.game_info.players:
            # 已经淘汰的成员没有资格发言.
            if player in exiled:
                continue
            # 用户已经发言过了.
            if player in round_info.votes:
                continue

            round_info.current_player = player
            # 轮到当前用户发言.
            if player == this.game_info.gaming.user_player:
                text = UndercoverGameDriver.ASK_USER_TO_VOTE_TEMP.format(player=player)
            # 轮到 AI 用户发言.
            else:
                text = UndercoverGameDriver.AI_COMMIT_VOTE_TEMP.format(player=player)
            # 发送消息.
            ctx.send_at(this).markdown(text)
            return ctx.mind(this).awaits()

        # 说明所有人发言已经结束了. 进入计票环节.
        return ctx.mind(this).forward(_VoteResultStage.stage_name)

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        # 获取当前用户.
        round_info = self._current_round_info(this)
        current_player = round_info.current_player
        if current_player == this.game_info.gaming.user_player:
            # 说明需要等待用户的回复.
            vote, op = self._receive_valid_text_message(ctx, this, False)
            if op is None:
                return op
            thought = ""
        else:
            # AI 发言环节.
            vote, thought = self._ai_player_commit_vote(ctx, this, current_player)

        # 设置好发言内容.
        # 必须是用户里的人.
        if vote in this.game_info.players:
            round_info.votes[current_player] = vote
            round_info.player_thoughts[current_player] = thought

            vote_count = round_info.vote_count(vote)

            text = UndercoverGameDriver.PLAYER_SPEAK_OUT_VOTE_TEMP.format(
                player=current_player,
                vote=vote,
                tickets=vote_count,
            )

        else:
            text = UndercoverGameDriver.VOTE_TARGET_NOT_EXISTS_TEMP.format(player=vote)

        # 结束, 并重新进入 activate.
        ctx.send_at(this).markdown(text)
        # 重启当前环节.
        return ctx.mind(this).repeat()


class _VoteResultStage(_AbsStage):
    """
    投票结果对外公示, 让所有 AI 可以看到 (其实就是放到下轮 Prompt 里)
    主要是为了让对话者看到结果.
    """

    stage_name = "vote_result"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:

        round_info = self._current_round_info(this)
        votes = []
        counts = {}
        exiled_player = ""
        exiled_votes = 0

        for player in round_info.votes:
            vote = round_info.votes[player]
            votes.append(f"- {player} 投票给: {vote}")
            # 计算票数.
            if vote in counts:
                counts[vote] += 1
            else:
                counts[vote] = 1
            vote_count = counts[vote]
            if vote_count > exiled_votes:
                exiled_player = vote
                exiled_votes = vote_count

        # 没有任何人投票出去?
        if not exiled_player:
            current_players = this.game_info.current_players()
            # 随机一下
            idx = randint(0, len(current_players) - 1)
            # 组织决定就你了.
            exiled_player = current_players[idx]
            result = f"没有人被投票出去, 组织决定将 {exiled_player} 淘汰"
        else:
            result = f"{exiled_player} 淘汰, 总得票 {exiled_votes}"

        # 淘汰者入列.
        this.game_info.gaming.exiled.append(exiled_player)
        round_info.result = result

        # 被淘汰的人说获奖感言.
        self._game_exiled_feeling(ctx, this, exiled_player)

        # 告知游戏信息.
        text = UndercoverGameDriver.ROUND_VOTES_TEMP.format(votes="\n".join(votes))
        result_text = UndercoverGameDriver.ROUND_RESULT_TEMP.format(result=result)
        ctx.send_at(this).markdown(text).markdown(result_text)
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        # 进入结算计算环节.
        current_players = set(this.game_info.current_players())
        if len(current_players) == 3:
            return ctx.mind(this).forward(_GameResultStage.stage_name)

        # 比较交集.
        undercover = set(this.game_info.gaming.undercover)
        if not undercover & current_players:
            return ctx.mind(this).forward(_GameResultStage.stage_name)

        # 否则就开始一个新的回合.
        this.game_info.gaming.round += 1
        return ctx.mind(this).forward(_RoundInitializeStage.stage_name)


class _GameResultStage(_AbsStage):
    """
    揭示游戏的结果.
    1. 如果游戏结束了, 对外发放结果.
    2. 如果游戏未结束, 则进入下一轮.
    """
    stage_name = "game_result"

    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        players = []
        undercover = set(this.game_info.gaming.undercover)
        for player in this.game_info.players:
            if player not in undercover:
                players.append(player)
        alive = set(this.game_info.current_players())

        winner_role = UndercoverGameDriver.UNDERCOVER_ROLE if undercover & alive else UndercoverGameDriver.PLAYER_ROLE
        for name in alive:
            self._game_over_feeling(ctx, this, name, winner_role)

        review_filename = self.driver.review_saving_filename()

        feelings = []
        for player in this.game_info.gaming.feelings:
            feeling = this.game_info.gaming.feelings[player]
            feelings.append(f"- {player}: {feeling}")

        text = UndercoverGameDriver.GAME_RESULT_TEMP.format(
            round=this.game_info.gaming.round + 1,
            players=",".join(players),
            undercover=",".join(undercover),
            alive=",".join(alive),
            winner=winner_role,
            filename=review_filename,
            feelings="\n".join(feelings)
        )
        ctx.send_at(this).markdown(text)
        self.driver.save_review_result(review_filename, this.game_info)
        # 仪式性地 wait 一下.
        return ctx.mind(this).awaits()

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        # 任务完成.
        return ctx.mind(this).finish()


# ----- reactions ----- #


class ShowRuleCmdReaction(CommandReaction):
    """
    展示游戏规则.
    """

    def __init__(
            self,
            name: str = "rule",
            desc: str = "show game rule",
            level: int = TaskLevel.LEVEL_PRIVATE,
    ):
        cmd = Command(
            name=name,
            desc=desc,
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: Thought, output: CommandOutput) -> Operator:
        ctx.send_at(this).markdown(UndercoverGameDriver.GAME_RULE)
        return ctx.mind(this).rewind()


class DebugCmdReaction(CommandReaction):

    def __init__(
            self,
            name: str = "debug",
            desc: str = "toggle debug mode",
            level: int = TaskLevel.LEVEL_PRIVATE,
    ):
        cmd = Command(
            name=name,
            desc=desc,
        )
        super().__init__(cmd, level)

    def on_output(self, ctx: Context, this: UndercoverGameThought, output: CommandOutput) -> Operator:
        debug_mode = not this.game_info.gaming.debug_mode
        this.game_info.gaming.debug_mode = debug_mode
        ctx.send_at(this).markdown(f"toggle debug mode to {debug_mode}")
        return ctx.mind(this).awaits()
