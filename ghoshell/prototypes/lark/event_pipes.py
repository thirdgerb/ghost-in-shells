# from ghoshell.shell.prototypes.lark.events import LarkEventCaller, Event, ImMessageReceive
#
# from ghoshell.ghost import Input
# from ghoshell.shell import IShell
# from ghoshell.framework.shell import EventMiddleware
# from ghoshell.framework.shell.shell import EventPipe, EventPipeline


# class ParseLarkEventToInputPipe(EventMiddleware):
#     """
#     将 Lark 的消息事件包装成 Ghost 的 Input
#     """
#
#     def new(self, shell: IShell) -> EventPipe:
#         def as_input(caller: LarkEventCaller, after: EventPipeline) -> Optional[Input]:
#             match caller.event_type:
#                 case ImMessageReceive.event_type():
#                     event = ImMessageReceive(**caller.event)
#                     return self._wrap_im_receive_event(event)
#                 case _:
#                     return after(caller)
#
#         return as_input
#
#     def _wrap_im_receive_event(self, e: ImMessageReceive) -> Input:
#         _input = self._wrap_common_event(e)
#         # 这里对 input 进行二次加工.
#         return _input
#
#     def _wrap_common_event(self, e: Event) -> Input:
#         return Input(
#
#         )
