from ghoshell.ghost import Mind
from ghoshell.ghost_fmk._operators import *


class MindImpl(Mind):

    def forward(self, *stages: str) -> "Operator":
        return ForwardOperator(self.this.tid, list(stages))

    def redirect_to(self, to: "URL") -> "Operator":
        pass

    def awaits(self) -> "Operator":
        return AwaitOperator(self.this.tid, self.this.url.stage)

    def depend_on(self, target: "URL") -> "Operator":
        return DependOnOperator(self.this.tid, self.this.url.stage, target)

    def repeat(self) -> "Operator":
        # 不变更状态.
        return AwaitOperator(self.this.tid, None)

    def restart(self) -> "Operator":
        return RestartOperator(self.this.tid)

    def rewind(self, repeat: bool = False) -> "Operator":
        return RewindOperator(repeat=repeat)

    def reset(self) -> "Operator":
        return ResetOperator()

    def quit(self) -> "Operator":
        return QuitOperator(self.this.tid, self.this.url.stage)

    def cancel(self) -> "Operator":
        return CancelOperator(self.this.tid, self.this.url.stage)

    def fail(self) -> "Operator":
        return FailOperator(self.this.tid, self.this.url.stage)
