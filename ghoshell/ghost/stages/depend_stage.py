# from __future__ import annotations
#
# from abc import abstractmethod
# from typing import Optional, ClassVar, List
#
# from ghoshell.ghost.context import Context
# from ghoshell.ghost.intentions.events import *
# from ghoshell.ghost.intentions.listeners import Listener, ListenerFnWrapper
# from ghoshell.ghost.intentions.stage import Stage
# from ghoshell.ghost.intentions.thought import Thought
# from ghoshell.ghost.operator import Operator
# from ghoshell.ghost.runtime import TASK_STATUS, TaskStatus
# from ghoshell.ghost.url import URL
#
#
# class DependStage(Stage, metaclass=ABCMeta):
#     status: ClassVar[TASK_STATUS] = TaskStatus.DEPENDING
#
#     @abstractmethod
#     def depend_on(self, this: Thought) -> URL:
#         pass
#
#     @abstractmethod
#     def on_callback(self, ctx: "Context", this: Thought, event: Callback) -> Optional[Operator]:
#         """
#         处理回调信息.
#         """
#         pass
#
#     def on_withdraw(self, ctx: "Context", this: Thought, event: Withdrawing) -> Optional[Operator]:
#         """
#         处理退出事件, 是否要中断或拦截.
#         """
#         # 默认不做任何拦截.
#         return None
#
#     def listeners(self) -> List[Listener]:
#         return [
#             ListenerFnWrapper(self.on_callback, Callback),
#             ListenerFnWrapper(self.on_withdraw, Withdrawing),
#         ]
#
#     def activate(self, ctx: "Context", this: Thought) -> Operator:
#         depend_url = self.depend_on(this)
#         # 目标任务有结果, 会直接触发 on_callback
#         # 否则会重定向到目标任务.
#         return ctx.mind(this).depend_on(depend_url)
