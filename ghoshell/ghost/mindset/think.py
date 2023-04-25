from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field

from ghoshell.ghost.context import Context
from ghoshell.ghost.mindset.intention import Intention
from ghoshell.ghost.mindset.stage import Stage
from ghoshell.ghost.mindset.thought import Thought
from ghoshell.ghost.url import URL


class ThinkMeta(BaseModel):
    """
    Think 的元数据.
    要求所有的 Think 都可以产出元数据, 使之可配置.
    这么做, 是为了可以在运行时动态生成 Think
    机器人也因此可以自己生产自己的 Think.
    """
    url: URL
    driver: str
    config: Dict = Field(lambda: {})


class Think(BaseModel, metaclass=ABCMeta):
    """
    ghost 拥有的思维模块
    """

    @abstractmethod
    def url(self) -> URL:
        """
        stage 必须为 ""
        """
        pass

    @abstractmethod
    def to_meta(self) -> ThinkMeta:
        """
        所有的 Think 都要求可以返回 Meta 数据.
        """
        pass

    @abstractmethod
    def description(self, thought: Thought) -> Any:
        pass

    @abstractmethod
    def new_task_id(self, ctx: "Context", args: Dict) -> str:
        """
        所有的 think 都要求可以根据上下文 + args 生成一个 id.
        这个 id 可以根据 Trace 自行推导
        用来做隔离, 在设计上决定是全局唯一的任务, 还是会话唯一, 又或是 clone 唯一等等.
        """
        pass

    @abstractmethod
    def new_thought(self, ctx: "Context", args: Dict) -> Thought:
        """
        结合上下文, 初始化一个 Thinking 的有状态实例.
        这个状态实例用 this 来表示, 传递给各种 Stage 的方法.
        相当于面向对象里的 this, 或 python 里的 self.
        由于我们本身用 Python 来驱动, 所以会存在 self 和 this 两个对象.
        self 持有的是 think 的 meta 数据, 全局是静态的, 而 this 持有的则是上下文相关的数据.
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

    @abstractmethod
    def intentions(self, ctx: Context) -> Optional[List["Intention"]]:
        """
        可以命中当前状态的各种 Intention
        可以被封装成为一个 Reaction
        """
        pass


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
