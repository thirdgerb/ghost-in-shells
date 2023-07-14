from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import List

from ghoshell.ghost.mindset.operator import Operator
from ghoshell.url import URL


class Mind(metaclass=ABCMeta):

    # ---- 思维重定向的命令 ---- #

    @abstractmethod
    def forward(self, *stages: str) -> "Operator":
        pass

    @abstractmethod
    def redirect(self, to: "URL") -> "Operator":
        """
        从当前任务, 进入一个目标任务.
        自己会根据实际状态, 被系统调度或垃圾回收.

        如果涉及到自身的状态变更, 更复杂的逻辑以后再实现
        """
        pass

    # ---- 中断命令 ---- #

    @abstractmethod
    def awaits(
            self,
            # 是否进入 waiting 状态并重定向.
            to: URL = None,
            # only reactions
            only: List[str] | None = None,
            # exclude reactions
            exclude: List[str] | None = None,
    ) -> "Operator":
        """
        await 是挂起当前任务. 可以通过 to 重定向到别的任务.
        如果 to 不存在, 则当前 上下文也会同步休眠, 等待下一次 input 的唤醒.
        而实际上, 当前 Process 进入了 wait 状态, 可能 clone 还不会立刻释放 (unlock), 而是继续去处理异步消息.
        就看具体怎么实现了.
        """
        pass

    @abstractmethod
    def yield_to(self, stage: str, callback: bool = False) -> "Operator":
        """
        尝试启动一个状态, 但是 fallback
        """
        pass

    @abstractmethod
    def depend_on(self, target: "URL") -> "Operator":
        """
        依赖一个目标任务, 目标任务完成后会发起回调.
        这个目标任务也可能在运行中, depend_on 不会去指定任何 stage.
        每个 Think 对于别的 Think 而言内部是封闭的.
        """
        pass

    # ---- 任务内部命令. ---- #

    @abstractmethod
    def repeat(self) -> "Operator":
        """
        重复上一轮交互的终点状态, 触发 OnRepeat 事件.
        Repeat 不必重复上一轮交互的所有输出, 只需要 Repeat 必要的输出.
        这个命令对于对话机器人比较有用, 比如机器人向用户询问了一个问题
        执行 Repeat 就会重复去问用户.

        用 LLM 可以将 Repeat 事件直接告知 LLM, 让它自行重复.
        """
        pass

    @abstractmethod
    def restart(self) -> "Operator":
        """
        重启当前的 Task. 与 go_stage('') 不同, 还会重置掉上下文状态 (重置 thought)
        """
        pass

    # ---- 取消流程 ---- #

    @abstractmethod
    def cancel(self) -> "Operator":
        """
        """
        pass

    @abstractmethod
    def fail(self) -> "Operator":
        """
        """
        pass

    # ---- 全局命令 ---- #

    @abstractmethod
    def rewind(self, repeat: bool = False) -> "Operator":
        """
        重置当前对话状态. 忽视本轮交互的变更.
        如果执行了 rewind, 理论上不会保存当前交互产生出来的 Process/Task 等变更
        而是当作什么都没发生过.
        如果要做更复杂的实现, 就不用 rewind 方法了.

        以前的 commune chatbot 不仅实现了 rewind, 还实现了 process snapshots
        可以通过 backward 指令返回 n 轮对话之前.
        这种 rollback 的能力极其复杂, 实际上没有任何办法完美实现.
        因为在思考运行的过程中, 必然有 IO 已经发生了.
        """
        pass

    @abstractmethod
    def reset(self) -> "Operator":
        """
        Reset 的对象是整个会话的 Process, 会清空所有任务回到起点.
        通常用于兼容一些低水平的异常. 出故障后重置状态
        对于不可恢复的异常, 也要有一整套恢复办法.

        典型的例子是 task 数据结构变化, 导致记忆回复时会产生 RuntimeException
        或者 intentions 做了无法向前兼容的改动, 导致 runtime 记忆出错.
        """
        pass

    @abstractmethod
    def quit(self) -> "Operator":
        """
        退出整个进程.
        会从 current_task 开始逐个 cancel, 一直 cancel 到 root
        这也意味着 cancel 的过程中可以中断.
        """
        pass

    @abstractmethod
    def finish(self) -> "Operator":
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass
