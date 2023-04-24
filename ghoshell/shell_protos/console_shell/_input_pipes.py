from ghoshell.ghost import Input, Output, TextMsg
from ghoshell.shell import ShellContext
from ghoshell.shell_fmk import InputMiddleware, InputPipe, InputPipeline


class InputTestMiddleware(InputMiddleware):

    def new(self, ctx: ShellContext) -> InputPipe:
        def pipe(_input: Input, after: InputPipeline):
            text = _input.payload.text
            # 拦截 text, 直接返回.
            if text is not None:
                output = Output.new(_input)
                message = TextMsg.new(raw=f"you said: {text.raw}")
                output.payload.append(message.new_payload())
                return _input, output

            return after(_input)

        return pipe
