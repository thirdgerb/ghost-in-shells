from typing import Optional

from ghoshell.ghost import Input
from ghoshell.shell import IShell
from ghoshell.shell.framework import EventMiddleware
from ghoshell.shell.framework.shell import EVENT_PIPE, EVENT_PIPELINE
from ghoshell.shell.prototypes.lark.events import LarkEventCaller, Event, ImMessageReceive


class ParseLarkEventToInputPipe(EventMiddleware):
    """
    将 Lark 的消息事件包装成 Ghost 的 Input
    """

    def new(self, shell: IShell) -> EVENT_PIPE:
        def as_input(caller: LarkEventCaller, after: EVENT_PIPELINE) -> Optional[Input]:
            match caller.event_type:
                case ImMessageReceive.event_type():
                    event = ImMessageReceive(**caller.event)
                    return self._wrap_im_receive_event(event)
                case _:
                    return after(caller)

        return as_input

    def _wrap_im_receive_event(self, e: ImMessageReceive) -> Input:
        _input = self._wrap_common_event(e)
        # 这里对 input 进行二次加工.
        return _input

    def _wrap_common_event(self, e: Event) -> Input:
        return Input(

        )
