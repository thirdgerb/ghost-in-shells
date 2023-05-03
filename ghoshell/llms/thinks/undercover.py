import time
from abc import ABCMeta, abstractmethod
from random import randint
from typing import Optional, List, Dict, Any, ClassVar, Tuple

from pydantic import BaseModel, Field

from ghoshell.ghost import *
from ghoshell.ghost_fmk.reactions import CommandReaction, Command, CommandOutput
from ghoshell.messages import *


# ----- Thought ----- #


class _RoundInfo(BaseModel):
    """
    轮次里的基本信息.
    """
    # 第几轮.
    round: int

    # 玩家的描述词
    describes: Dict[str, str] = Field(default_factory=dict)

    # 玩家的投票结果
    votes: Dict[str, str] = Field(default_factory=dict)

    # 每个活跃玩家这一轮的思考内容.
    # 会带到下一轮游戏中, 作为他的思考上下文.
    player_thoughts: Dict[str, str] = Field(default_factory=dict)

    # 当前发言的用户
    current_player: str = ""

    def vote_count(self, vote: str) -> int:
        vote_count = 0
        for player in self.votes:
            voted = self.votes[player]
            if voted == vote:
                vote_count += 1
        return vote_count


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
    # 游戏退出时就遗忘.
    priority = -1

    def __init__(self, args: Dict):
        self.game_info = _UndercoverGameInfo()
        super().__init__(args)

    def prepare(self, args: Dict) -> None:
        return None

    def set_variables(self, variables: Dict) -> None:
        self.game_info = _UndercoverGameInfo(**variables)

    def vars(self) -> Dict | None:
        _vars = self.game_info.dict()
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

    VOTE_RESULT_TEMP: ClassVar[str] = """
本轮游戏投票如下:

{votes}


系统判定: {result}
"""

    GAME_RESULT_TEMP: ClassVar[str] = """
游戏结束!

- 游戏轮次: {round}
- 普通玩家阵营: {players}
- 卧底阵营: {undercover}
- 最后存活玩家: {alive}

恭喜{winner}方获得最后的胜利!

游戏数据保存在 {filename}

(输入任何内容结束)
"""

    DESCRIBE_PROMPT_TEMP: ClassVar[str] = """
我在玩 "谁是卧底" 的小游戏. 游戏的基本信息如下:

{context}

---

当前游戏的状态: 

{game_status}

--- 

游戏进行过程的信息如下: 

{game_process}

---

现在是第 {round} 轮, 我需要描述自己提示词所描述的事物. 

我是第 {commit_n} 个发言, 之前的发言如下: 

{commits}

我需要考虑的是:
- 我的描述不能偏离拿到的词  
- 卧底会尽可能隐藏自己卧底身份
- 普通玩家会尽可能误导卧底

我对 {my_word} 的描述是:  
"""

    VOTE_PROMPT_TEMP: ClassVar[str] = """
我在玩 "谁是卧底" 的小游戏. 游戏的基本信息如下:

{context}

---

当前游戏的状态: 

{game_status}

--- 

游戏进行过程的信息如下: 

{game_process}

---

现在是第 {round} 轮, 我需要投票. 本轮所有人的发言是: 

{commits}


我需要考虑的是:
- 我的描述不能偏离拿到的词  
- 卧底会尽可能隐藏自己卧底身份
- 普通玩家会尽可能误导卧底

我对 {my_word} 的描述是:  
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
第 {round} 轮游戏开始!

(输入任何信息继续)
"""

    ROUND_DESCRIBE_SUMMARY_TEMP: ClassVar[str] = """
第 {round} 轮发言完毕. 所有人的发言结果是:

{commits}
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
        print(filename, game_info.dict())


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
        return URL.new_resolver(self.driver.think_name)

    def to_meta(self) -> ThinkMeta:
        return self.driver.to_meta()

    def description(self, thought: Thought) -> Any:
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
        return self.url().new_id(extra=ctx.input.trace.dict(include={"session_id"}))

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
        return URL(resolver=self.driver.think_name, stage=self.stage_name)

    def intentions(self, ctx: Context) -> List[Intention] | None:
        return None

    def reactions(self) -> Dict[str, Reaction]:
        return {
            "/rule": ShowRuleCmdReaction(),
        }

    def on_event(self, ctx: "Context", this: UndercoverGameThought, event: Event) -> Operator | None:
        if isinstance(event, OnActivating):
            return self.on_activate(ctx, this)
        if isinstance(event, OnReceived):
            return self.on_received(ctx, this)
        return None

    @abstractmethod
    def on_activate(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        pass

    @abstractmethod
    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        pass

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
            return ctx.mind(this).forward(_GameResultStage.stage_name)

        # 有必要的话, 初始化 round
        current_round = this.game_info.gaming.round
        if current_round == len(this.game_info.gaming.rounds):
            new_round = _RoundInfo(round=current_round)
            this.game_info.gaming.rounds.append(new_round)

        text = UndercoverGameDriver.ROUND_START_TEMP.format(round=current_round + 1)
        ctx.send_at(this).markdown(text)
        return ctx.mind(this).forward(_RoundCommitStage.stage_name)

    def on_received(self, ctx: "Context", this: UndercoverGameThought) -> Operator | None:
        """
        任何消息直接进入.
        """
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
            if player in round_info.describes:
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
        for player in round_info.describes:
            commit = round_info.describes[player]
            commits.append(f"- {player} 发言是: {commit}")
        summary = UndercoverGameDriver.ROUND_DESCRIBE_SUMMARY_TEMP.format(
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
            content = self._ai_describe(ctx, this, current_player)

        # 设置好发言内容.
        round_info.describes[current_player] = content
        text = UndercoverGameDriver.PLAYER_SPEAK_OUT_DESCRIBE_TEMP.format(
            player=current_player,
            content=content,
        )
        ctx.send_at(this).markdown(text)
        # 重启当前环节.
        return ctx.mind(this).repeat()

    def _ai_describe(self, ctx: "Context", this: UndercoverGameThought, player: str) -> str:
        return "测试测试"


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
            vote, thought = self._ai_vote(ctx, this, current_player)

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

    def _ai_vote(self, ctx: "Context", this: UndercoverGameThought, player: str) -> Tuple[str, str]:
        # todo
        return this.game_info.current_players()[0], "思考内容"
        # return "投票对象", "思考内容"


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
        # 被淘汰的人说获奖感言.
        exiled_feeling = self._exited_feeling(ctx, this, exiled_player)
        this.game_info.gaming.feelings[exiled_player] = exiled_feeling

        # 告知游戏信息.
        text = UndercoverGameDriver.VOTE_RESULT_TEMP.format(
            votes="\n".join(votes),
            result=result,
        )
        ctx.send_at(this).markdown(text)
        return ctx.mind(this).awaits()

    def _exited_feeling(self, ctx: Context, this: UndercoverGameThought, exiled: str) -> str:
        return "feeling"

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

        winner = UndercoverGameDriver.PLAYER_ROLE
        for name in alive:
            if name in undercover:
                winner = UndercoverGameDriver.UNDERCOVER_ROLE
                break

        review_filename = self.driver.review_saving_filename()

        text = UndercoverGameDriver.GAME_RESULT_TEMP.format(
            round=this.game_info.gaming.round + 1,
            players=",".join(players),
            undercover=",".join(undercover),
            alive=",".join(alive),
            winner=winner,
            filename=review_filename,
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
