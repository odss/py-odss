import asyncio
import logging
import typing as t
from time import monotonic

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

    def create_task(self, target, *args) -> asyncio.Future:
        assert target
        if asyncio.iscoroutine(target):
            return self.loop.create_task(target)
        elif asyncio.iscoroutinefunction(target):
            return self.loop.create_task(target(*args))
        elif is_callback(target):
            return self.run_in_future(target, *args)
        raise TypeError(
            "Incorrect type of target. Excpected coroutine or coroutinefunction"
        )

    def create_job(self, target, *args) -> asyncio.Future:
        return self.loop.run_in_executor(None, target, *args)

    async def collect_tasks(self, targets) -> None:
        tasks = [self.create_task(method, *args) for method, *args in targets]
        start_time = monotonic()

        pending = [task for task in tasks if not task.done()]
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
