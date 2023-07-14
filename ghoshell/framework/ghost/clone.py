from abc import ABCMeta

from ghoshell.framework.ghost.config import GhostConfig
from ghoshell.ghost import *


class CloneImpl(Clone, metaclass=ABCMeta):

    def __init__(self, ghost: Ghost, clone_id: str, config: GhostConfig):
        self._ghost = ghost
        self._clone_id = clone_id
        # 对 Ghost 级别的容器做了二次封装, 方便注册 clone 级别的单例.
        # 注册的动作应该在 Ghost.new_clone(clone_id) 方法里实现.
        # 指定了 CloneConfig 的强类型.
        self._config = config
        # 尽可能把工程方法放到 ghost 里.
        self._mindset = ghost.mindset.clone(clone_id)
        self._focus = ghost.focus.clone(clone_id)
        self._memory = ghost.memory.clone(clone_id)

    @property
    def clone_id(self) -> str:
        return self._clone_id

    @property
    def ghost(self) -> Ghost:
        return self._ghost

    @property
    def root(self) -> "URL":
        return self._config.root_url.copy_with()

    @property
    def mindset(self) -> "Mindset":
        return self._mindset

    @property
    def memory(self) -> "Memory":
        return self._memory

    @property
    def focus(self) -> "Focus":
        return self._focus

    def destroy(self) -> None:
        # 清除 clone 级别的实例.
        # 如果不是请求级别的实例, destroy 方法不需要实现.
        self._mindset.destroy()
        self._focus.destroy()
        self._memory.destroy()

        # 删除持有.
        del self._ghost
        del self._config
        del self._focus
        del self._mindset
        del self._clone_id
        del self._focus
        del self._memory
