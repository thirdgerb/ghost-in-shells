from ghoshell.ghost import Task, URL, Process, RuntimeException, TaskStatus


def test_task_init():
    task = Task(tid="a", url=URL(resolver="hello"))
    assert task is not None


def test_process_init():
    p = Process.new_process("sid", "pid")
    a = Task(tid="a", url=URL(resolver="a"))
    p.store_task(a)
    assert p.root == "a"
    assert p.current == "a"


def test_process_store_await_tasks():
    p = Process.new_process("sid", "pid")
    a = Task(tid="a", url=URL(resolver="a"))
    p.store_task(a)

    b = Task(tid="b", url=URL(resolver="b"))
    assert p.root == "a"
    e = None
    try:
        p.set_current("b")
    except RuntimeException as err:
        e = err
    assert e is not None

    p.store_task(b)
    p.set_current("b")
    assert p.current == "b"
    assert p.root == "a"


def test_process_store_canceled_task():
    p = Process.new_process("sid", "pid")
    a = Task(tid="a", url=URL(resolver="a"))
    b = Task(tid="b", url=URL(resolver="b"))
    p.store_task(a)
    p.store_task(b)
    assert p.running == ["b", "a"]

    b.status = TaskStatus.CANCELING
    p.store_task(b)
    assert p.running == ["a"]
    assert p.canceling == ["b"]

    # canceling fallback
    assert p.fallback() is b


def test_process_store_same_task():
    p = Process.new_process("sid", "pid")
    a = Task(tid="a", url=URL(resolver="a"))
    p.store_task(a, a, a, a, a)
    p.reset_indexes()
    assert len(p.tasks) == 1
