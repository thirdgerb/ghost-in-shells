from ghoshell.framework.ghost.operators import *
from ghoshell.ghost import Mind


class MindImpl(Mind):

    def __init__(self, tid: str, url: URL):
        self.tid = tid
        self.url = url

    def forward(self, *stages: str) -> "Operator":
        return ForwardOperator(self.tid, list(stages), self.url)

    def redirect(self, to: "URL") -> "Operator":
        return ActivateOperator(to, self.url, None)

    def yield_to(self, stage: str, callback: bool = False) -> "Operator":
        return YieldToOperator(self.tid, stage, callback, self.url)

    def awaits(
            self,
            to: URL | None = None,
            only: List[str] | None = None,
            exclude: List[str] | None = None,
    ) -> "Operator":
        return AwaitOperator(self.tid, self.url.stage, only, exclude, self.url, to=to)

    def depend_on(self, target: "URL") -> "Operator":
        return DependOnOperator(self.tid, self.url.stage, target, self.url)

    def repeat(self) -> "Operator":
        # 不变更状态.
        return ActivateOperator(self.url, self.url, self.tid)

    def restart(self) -> "Operator":
        return RestartOperator(self.tid, self.url)

    def rewind(self, repeat: bool = False) -> "Operator":
        return RewindOperator(repeat=repeat, fr=self.url)

    def reset(self) -> "Operator":
        return ResetOperator(self.url)

    def quit(self) -> "Operator":
        return QuitOperator(self.tid, self.url.stage, self.url)

    def cancel(self) -> "Operator":
        return CancelOperator(self.tid, self.url.stage, self.url)

    def fail(self) -> "Operator":
        return FailOperator(self.tid, self.url.stage, self.url)

    def finish(self) -> "Operator":
        return FinishOperator(self.tid, self.url.stage, self.url)

    def destroy(self) -> None:
        del self.tid
        del self.url
