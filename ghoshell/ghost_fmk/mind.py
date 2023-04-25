from ghoshell.ghost import Mind
from ghoshell.ghost_fmk._operators import *


class MindImpl(Mind):

    def __init__(self, tid: str, url: URL):
        self.tid = tid
        self.url = url

    def forward(self, *stages: str) -> "Operator":
        return ForwardOperator(self.tid, list(stages))

    def redirect(self, to: "URL") -> "Operator":
        return ActivateOperator(to, self.url, None)

    def yield_to(self, stage: str, callback: bool = False) -> "Operator":
        return YieldToOperator(self.tid, stage, callback)

    def awaits(self, only: List[str] | None = None, exclude: List[str] | None = None) -> "Operator":
        return AwaitOperator(self.tid, self.url.stage, only, exclude)

    def depend_on(self, target: "URL") -> "Operator":
        return DependOnOperator(self.tid, self.url.stage, target)

    def repeat(self) -> "Operator":
        # 不变更状态.
        return AwaitOperator(self.tid, None, None, None)

    def restart(self) -> "Operator":
        return RestartOperator(self.tid)

    def rewind(self, repeat: bool = False) -> "Operator":
        return RewindOperator(repeat=repeat)

    def reset(self) -> "Operator":
        return ResetOperator()

    def quit(self) -> "Operator":
        return QuitOperator(self.tid, self.url.stage)

    def cancel(self) -> "Operator":
        return CancelOperator(self.tid, self.url.stage)

    def fail(self) -> "Operator":
        return FailOperator(self.tid, self.url.stage)

    def destroy(self) -> None:
        del self.tid
        del self.url
