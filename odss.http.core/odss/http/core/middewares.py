import typing as t
import bisect


class Middlewares:
    def __init__(self):
        self.middlewares = []

    def add(self, middleware: t.Callable, priority: t.Tuple[int, int] = None):
        priority = priority if priority is not None else (0, 0)
        keys = [mid[1] for mid in self.middlewares]
        idx = bisect.bisect_left(keys, priority)
        self.middlewares.insert(idx, (middleware, priority))

        def remove_middleware():
            self.remove(middleware, priority)

        return remove_middleware

    def remove(self, middleware: t.Callable, priority: t.Tuple[int, int] = None):
        priority = priority if priority is not None else (0, 0)
        keys = [mid[1] for mid in self.middlewares]
        idx = bisect.bisect_left(keys, priority)
        self.middlewares.pop(idx)

    def reset(self):
        self.middlewares = None

    def all(self):
        return self.middlewares[::-1]
