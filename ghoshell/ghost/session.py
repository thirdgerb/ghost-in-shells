from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Dict


class Session(metaclass=ABCMeta):
    """
    Session 是 Clone 的会话存储.
    一个 Clone 可能同时处于多个 Session 中, Session 做的是事件流 (input/output) 的隔离.
    举个例子, 聊天机器人可能同时在 多个私聊/群聊 里:
    clone_id 确保它跨群共享记忆, 但 session 保证和 不同的人/不同的群 对话不会相互干扰
    """

    @property
    @abstractmethod
    def clone_id(self) -> str:
        """
        session 所处的 clone
        """
        pass

    @property
    @abstractmethod
    def session_id(self) -> str:
        """
        session 自身的 ID.
        """
        pass

    def is_new(self) -> bool:
        """
        是否是新 session
        """
        pass

    @abstractmethod
    def new_process_id(self) -> str:
        """
        生成一个新的 process id
        """
        pass

    def current_process_id(self) -> str:
        """
        获取当前的 process id
        """
        pass

    @abstractmethod
    def new_message_id(self) -> str:
        """
        生成一个新的 message id.
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Dict) -> bool:
        """
        向 Session 中存入一个数据. 和 Session 一起过期.
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Dict | None:
        """
        从 session 中读取一个数据.
        """
        pass

    @abstractmethod
    def remove(self, *key: str) -> None:
        """
        删除 session 中的数据.
        """
        pass

    @abstractmethod
    def lock(self, key: str, overdue: int = -1) -> bool:
        """
        session 给一个 key 上锁.
        """
        pass

    @abstractmethod
    def unlock(self, key: str) -> bool:
        """
        session 给一个 key 解锁. 注意这里并没有强行要求上锁成功才能解锁.
        """
        pass

    @abstractmethod
    def get_task_data(self, tid: str) -> Dict | None:
        pass

    @abstractmethod
    def set_task_data(self, tid: str, value: Dict, overdue: int) -> None:
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """
        清空 Session 内的数据.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
