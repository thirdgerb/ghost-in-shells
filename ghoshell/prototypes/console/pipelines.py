import uuid

from ghoshell.framework.shell import ShellInputPipe, InputPipe, InputPipeline
from ghoshell.messages import Input, Output, Text
from ghoshell.shell import Shell


#
class InputTestMiddleware(ShellInputPipe):

    def new(self, shell: Shell) -> InputPipe:
        def pipe(_input: Input, after: InputPipeline):
            text = Text.read(_input.payload)
            # 拦截 text, 直接返回.
            if text is not None:
                output = Output.new(uuid.uuid4().hex, _input)
                message = Text(content=f"you said: {text.content}")
                message.join(output.payload)
                return _input, [output]

            return after(_input)

        return pipe
