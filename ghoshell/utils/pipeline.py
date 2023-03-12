from typing import Callable, List, TypeVar

PI = TypeVar('PI')
PO = TypeVar('PO')

PIPELINE = Callable[[PI], PO]
PIPE = Callable[[PI, PIPELINE], PO]


def create_pipeline(pipes: List[PIPE[PI, PO]], destination: PIPELINE[PI, PO]):
    """
    生成一个管道, 允许每个 pipe 自行中断.
    """

    def wrapper(pipe: PIPE, next_caller: PIPELINE):
        def fn(req):
            return pipe(req, next_caller)

        return fn

    caller = destination
    for p in reversed(pipes):
        caller = wrapper(p, caller)
    return caller
