import bisect
import typing as t


Priority: t.TypeAlias = tuple[int, int]
Middleware = t.Callable

class Middlewares:
    def __init__(self):
        self.middlewares: list[tuple[Middleware, Priority]] = []

    def add(self, middleware: t.Callable, priority: tuple[int, int]):
        keys = [mid[1] for mid in self.middlewares]
        idx = bisect.bisect_left(keys, priority)
        self.middlewares.insert(idx, (middleware, priority))

        def remove_middleware():
            self.remove(middleware, priority)

        return remove_middleware

    def remove(self, middleware: t.Callable, priority: tuple[int, int]):
        priority = priority or (0, 0)
        keys = [mid[1] for mid in self.middlewares]
        idx = bisect.bisect_left(keys, priority)
        self.middlewares.pop(idx)

    def reset(self):
        self.middlewares = []

    def all(self):
        return self.middlewares[::-1]
