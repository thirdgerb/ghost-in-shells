from typing import Optional

from ghoshell.ghost import *


class SendingImpl(Sending):

    def __init__(self, this: Thought, ctx: Context):
        self.this = this
        self.ctx = ctx
        self._output_buffer: Output | None = None

    def output(self, *messages: "Message", trace: Trace | None = None) -> "Sending":

        if trace is not None:
            self._deliver_sync_output()

        for message in messages:
            self._refresh_sync_output(trace)
            success = message.join_payload(self._output_buffer.payload)
            if not success:
                self._deliver_sync_output()
                self._refresh_sync_output(trace)
                message.join_payload(self._output_buffer.payload)
        return self

    def _deliver_sync_output(self) -> None:
        if self._output_buffer is None:
            return
        self.ctx.output(self._output_buffer)
        self._output_buffer = None

    def _refresh_sync_output(self, trace: Trace | None) -> None:
        if self._output_buffer is None:
            # refresh
            mid = self.ctx.session.new_message_id()
            self._output_buffer = Output.new(mid, self.ctx.input, trace)

    def async_input(
            self,
            message: Message,
            pid: str | None = None,
            trace: Optional["Trace"] = None,
            tid: str | None = None,
    ) -> None:
        self_id = self.ctx.clone.clone_id
        if pid is None:
            pid = self.ctx.session.new_process_id()
        if tid is None:
            tid = ""
        if trace is None:
            inpt = self.ctx.input
            # 默认保持相同的会话.
            trace_data = dict(
                clone_id=self_id,
                shell_id=inpt.trace.shell_id,
                shell_kind=inpt.trace.shell_kind,
                session_id=inpt.trace.session_id,
                process_id=pid,
                subject_id=inpt.trace.subject_id,
            )
        else:
            trace_data = trace.dict()

        # 实例化.
        mid = self.ctx.session.new_message_id()
        async_input = Input(
            mid=mid,
            payload=dict(
                tid=tid,
                body={
                    message.KIND: message.dict(),
                }
            ),
            trace=trace_data,
            is_async=True,
        )
        self.ctx.async_input(async_input)
        return

    def destroy(self) -> None:
        # deliver
        self._deliver_sync_output()

        # del
        del self._output_buffer
        del self.this
        del self.ctx
