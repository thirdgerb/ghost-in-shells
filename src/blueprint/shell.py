from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from typing import Optional, Tuple
    from .io import Input, Output
    from .ghost import Ghost

SHELL_KIND = TypeVar('SHELL_KIND', bound=str)


class Shell(metaclass=ABCMeta):

    @property
    @abstractmethod
    def kind(self) -> SHELL_KIND:
        pass

    @abstractmethod
    def connect(self, inpt: Input) -> Ghost:
        """
        根据 input, 得到与 ghost 的连接
        """
        pass

    @abstractmethod
    def on_input(self) -> Tuple[Input, Optional[Output]]:
        """
        处理输入信息, 并生成为 Input
        如果生成了 Output, 则意味着 Shell 可以独立生成 Output, 不需要联系 Ghost
        """
        pass

    @abstractmethod
    def on_output(self, output: Output) -> None:
        """
        响应输出的消息.
        可以用来消费异步逻辑.
        """
        pass

    def failed(self, inpt: Input, e: Optional[Exception]) -> None:
        pass

    def tick(self) -> None:
        # todo: 解决 try catch 问题.
        inpt, output = self.on_input()
        if output:
            # 如果 output 存在, 则直接走 output 路径
            self.on_output(output)
            return
        ghost = self.connect(inpt)
        # 尝试抢锁.
        if not ghost.lock():
            # todo, 加入未加锁异常.
            self.failed(inpt, None)
            return None
        output = ghost.react(inpt)
        self.on_output(output)
