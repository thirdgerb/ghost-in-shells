# from __future__ import annotations
#
# from abc import abstractmethod
# from typing import Optional, ClassVar, List
#
# from ghoshell.ghost import Intention
# from ghoshell.ghost.context import Context
# from ghoshell.ghost.mindset import Stage, Listener
# from ghoshell.ghost.mindset.events import *
# from ghoshell.ghost.mindset.thought import Thought
# from ghoshell.ghost.operator import Operator
# from ghoshell.ghost.runtime import TASK_STATUS, TaskStatus
# from ghoshell.ghost.url import URL
#
#
# class AwaitStage(Stage, metaclass=ABCMeta):
#     status: ClassVar[TASK_STATUS] = TaskStatus.AWAITING
#
#     @abstractmethod
#     def on_activate(self, ctx: "Context", this: Thought) -> None:
#         pass
#
#     def activate(self, ctx: "Context", this: Thought) -> Optional[Operator]:
#         self.on_activate(ctx, this)
#         return ctx.mind(this).await_input()
#
#     def stages
#
#     def on_fallback(self):
#
#     def listeners(self) -> List[Listener]:
#         pass
#
#
#
#
#
