from asyncio import sleep, get_event_loop, wait


def test_async_runner():
    class Tester:

        queue = []

        closed = False

        i = 0

        async def pop_input(self) -> int:
            while not (self.closed and len(self.queue) == 0):
                if len(self.queue) > 0:
                    return self.queue.pop(0)
                await sleep(0.1)

        def push_input(self, _input: int) -> None:
            self.queue.append(_input)

        def react(self, _input: int) -> int:
            return _input + 3

        async def run(self, plus) -> None:
            while not self.closed:
                _input = await self.pop_input()
                plus(self.react(_input))

    class Result:
        val = 0

        def plus(self, i):
            self.val += i

    t = Tester()
    r = Result()

    async def add_int():
        val = 1
        for idx in range(10):
            t.push_input(val)
            val += 1
            await sleep(0.3)
        t.closed = True

    loop = get_event_loop()
    cors = wait([add_int(), t.run(r.plus)])
    loop.run_until_complete(cors)

    assert r.val == 30 + 11 * 5
