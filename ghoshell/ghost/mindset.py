from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, Dict, List, Iterator

from pydantic import BaseModel, Field

from ghoshell.ghost.attention import Intention
from ghoshell.ghost.context import Context
from ghoshell.ghost.exceptions import MindsetNotFoundException
from ghoshell.ghost.operator import Operator
from ghoshell.ghost.uml import UML


class Thought(metaclass=ABCMeta):
    """
    当前任务的状态.
    可以理解成一个函数的运行栈
    args 是入参
    vars 则是运行中的变量.
    result 对应了 return 的值.

    这个 This 需要每个 Think 能力自定义一个协议.
    """

    # 任务的唯一 ID
    tid: str

    # 入参数据
    args: Dict

    # 对应的 think
    think: str

    def __init__(self, task_id: str, think: str, args: Dict):
        self.tid = task_id
        self.think = think
        self.args = args
        self.prepare(args)

    # ---- 抽象方法 ---- #
    @abstractmethod
    def prepare(self, args: Dict) -> None:
        """
        初始化
        """
        pass

    @abstractmethod
    def set_variables(self, variables: Dict) -> None:
        """
        设置上下文数据, 通常是一个 dict, 可以用 BaseModel 转成协议.
        """
        pass

    @abstractmethod
    def vars(self) -> Dict:
        """
        返回当前上下文中的变量.
        """
        pass

    @abstractmethod
    def result(self) -> Optional[Dict]:
        """
        从当前状态中返回一个结果.
        """
        pass


class Event(metaclass=ABCMeta):
    """
    事件机制
    """

    this: Thought
    kind: str

    @abstractmethod
    def destroy(self):
        """
        为了方便 python 的 gc
        主动删除掉一些持有元素
        避免循环依赖.
        """
        pass


class ThinkMeta(BaseModel):
    """
    Think 的元数据.
    要求所有的 Think 都可以产出元数据, 使之可配置.
    这么做, 是为了可以在运行时动态生成 Think
    机器人也因此可以自己生产自己的 Think.
    """
    uml: UML
    driver: str
    config: Dict = Field(lambda: {})


class Think(BaseModel, metaclass=ABCMeta):
    """
    ghost 拥有的思维模块
    """

    @abstractmethod
    def to_meta(self) -> ThinkMeta:
        """
        所有的 Think 都要求可以返回 Meta 数据.
        """
        pass

    @abstractmethod
    def uml(self) -> UML:
        """
        用类似 url (uniform resource locator) 的方式定位一个 Thinking
        实际上可以定义一个 args 协议
        用别的方法生成 uml
        """
        pass

    @abstractmethod
    def new_task_id(self, ctx: Context, args: Dict) -> str:
        """
        所有的 think 都要求可以根据上下文 + args 生成一个 id.
        这个 id 可以根据 Trace 自行推导
        用来做隔离, 在设计上决定是全局唯一的任务, 还是会话唯一, 又或是 clone 唯一等等.
        """
        pass

    @abstractmethod
    def new_thought(self, ctx: Context, args: Dict) -> Thought:
        """
        结合上下文, 初始化一个 Thinking 的有状态实例.
        这个状态实例用 this 来表示, 传递给各种 Stage 的方法.
        相当于面向对象里的 this, 或 python 里的 self.
        由于我们本身用 Python 来驱动, 所以会存在 self 和 this 两个对象.
        self 持有的是 think 的 meta 数据, 全局是静态的, 而 this 持有的则是上下文相关的数据.
        """
        pass

    @abstractmethod
    def overdue(self) -> int:
        """
        think 的过期时间.
        当话题结束或中断后, overdue 决定什么时候这个思路被遗忘.
        """
        pass

    @abstractmethod
    def result(self, this: Thought) -> Optional[Dict]:
        """
        当 Think 进入 finished 状态, 可以通过 result 方法返回一个结果.
        这个结果会被依赖当前 Think 的任务拿到
        从这个角度看, Think 相当于一个函数, 而 result 方法相当于函数的 return 方法.
        """
        pass

    @abstractmethod
    def all_stages(self) -> List[str]:
        """
        返回所有可能的状态名.
        一定有一个默认的状态, 状态名是 "" (default)
        许多任务很可能只有一个状态
        """
        pass

    @abstractmethod
    def fetch_stage(self, stage_name: str = "") -> Optional[Stage]:
        """
        获取 stage
        """
        pass

    @property
    def level(self) -> int:
        """
        think 自身的 level 由初始节点决定.
        """
        return self.fetch_stage().level()

    def intentions(self, ctx: Context) -> Optional[List["Intention"]]:
        """
        可以命中当前任务的各种 Intentions
        """
        return self.fetch_stage().intentions(ctx)


class ThinkDriver(metaclass=ABCMeta):
    """
    实现 Think 的驱动.
    通过 meta 的不同, 可以实例化出多个 Think
    """

    @abstractmethod
    def driver_name(self) -> str:
        """
        驱动的名称. 用来和 ThinkMeta 配对.
        """
        pass

    @abstractmethod
    def from_meta(self, meta: ThinkMeta) -> "Think":
        """
        可以根据 meta, 生产出 Think 的实例.
        这样, 机器人可以用一个 ConfigStorage 来读取 meta 数据
        然后实例化成 Think.
        当 meta 被修改时, 机器人的状态在线也会变更.
        """
        pass


class Stage(metaclass=ABCMeta):
    """
    Thinking 的状态位.
    状态位有一些基本的类型, 可以分为两大类:
    1. 中断的状态位, 等待
    """

    @abstractmethod
    def think(self) -> str:
        """
        Stage 都会对应一个 Think
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """
        Stage 在 Think 内的唯一 ID.
        """
        pass

    @abstractmethod
    def level(self) -> int:
        """
        Stage 当前的隔离级别, 详见 TaskLevel
        """
        pass

    @abstractmethod
    def intentions(self, ctx: Context) -> Optional[List["Intention"]]:
        """
        可以命中当前状态的各种 Intention
        """
        pass

    @abstractmethod
    def on_event(self, ctx: Context, e: "Event") -> "Operator":
        """
        当一个算子执行到当前位置时, 可以定义事件的响应逻辑.
        做必要的动作, 或者终止当前算子的执行, 开启一个新流程.
        常见的事件算子: 依赖回调, 取消, 退出, 异常等.
        """
        pass


class Mindset(metaclass=ABCMeta):
    """
    定义了 Ghost 拥有的思维方式
    核心是可以通过 UniformReactionLocator 取出 Reaction
    """

    @abstractmethod
    def fetch(self, thinking: str) -> Optional[Think]:
        """
        获取一个 Thinking
        """
        pass

    @abstractmethod
    def fetch_meta(self, thinking: str) -> Optional[ThinkMeta]:
        """
        获取一个 Thinking的 Meta, 如果存在的话.
        """
        pass

    def force_fetch(self, thinking: str) -> Think:
        """
        随手放一个语法糖方便自己.
        """
        fetched = self.fetch(thinking)
        if fetched is None:
            raise MindsetNotFoundException("todo message")
        return fetched

    @abstractmethod
    def register_sub_mindset(self, mindset: Mindset) -> None:
        """
        注册子级 mindset
        父级里查不到, 就到 sub mindset 里查
        这样的话, 就可以实现 mindset 的继承和重写.
        Clone 可以因此拥有和 Ghost 不同的 Mindset
        """
        pass

    @abstractmethod
    def register_driver(self, driver: ThinkDriver) -> None:
        """
        注册 think 的驱动.
        """
        pass

    @abstractmethod
    def register_meta(self, meta: ThinkMeta) -> None:
        """
        注册一个 thinking
        当然, Mindset 可以有自己的实现, 从某个配置体系中获取.
        或者合并多个 Mindset.
        """
        pass

    def register_think(self, think: Think) -> None:
        """
        用现成的 Think 完成注册.
        """
        meta = think.to_meta()
        self.register_meta(meta)
        if isinstance(think, ThinkDriver):
            self.register_driver(think)

    @abstractmethod
    def foreach_think(self) -> Iterator[Think]:
        """
        需要提供一种机制, 遍历所有的 Think 对象.
        """
        pass
