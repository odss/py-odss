import asyncio
import inspect
import logging
import typing as t
from time import monotonic
from collections.abc import Awaitable

logger = logging.getLogger(__name__)


def Callback(func: t.Callable) -> t.Callable:
    """Decorator for method safe to event loop."""
    setattr(func, "__odss-callback__", True)
    return func


def is_callback(func: t.Callable[..., t.Any]) -> bool:
    """Check if function is safe to be called in loop."""
    return getattr(func, "__odss-callback__", False) is True


BLOCK_LOG_TIMEOUT = 10


class TaskRunner:
    def __init__(self, loop):
        self.loop = loop

    def add_task(self, target, *args) -> asyncio.Task:
        assert target
        if asyncio.iscoroutine(target):
            return self.loop.create_task(target)
        elif asyncio.iscoroutinefunction(target):
            return self.loop.create_task(target(*args))
        elif inspect.ismethod(target):
            self.loop.call_soon(target, *args)
            return None
        raise TypeError(
            "Incorrect type of target. Excpected function, coroutine or coroutinefunction"
        )

    def add_tasks(self, targets) -> asyncio.Task:
        return [self.add_task(target, *args) for target, *args in targets]

    def run_job(self, target, *args) -> asyncio.Future:
        return self.loop.run_in_executor(None, target, *args)

    async def wait_for_tasks(self, tasks) -> t.Awaitable:
        start_time = monotonic()

        pending = [task for task in tasks if task and not task.done()]
        while pending:
            _, pending = await asyncio.wait(pending, timeout=BLOCK_LOG_TIMEOUT)
            wait_time = monotonic() - start_time
            for task in pending:
                logger.warning("Waited %s seconds for task: %s", wait_time, task)

    def run_in_future(self, target, *args) -> asyncio.Future:
        future = self.loop.create_future()
        try:
            future.set_result(target(*args))
        except Exception as ex:
            future.set_exception(ex)
        return future
