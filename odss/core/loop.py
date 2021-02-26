import asyncio
import logging
import typing as t

logger = logging.getLogger(__name__)

def Callback(func: t.Callable) -> t.Callable:
    """Decorator for method safe to event loop."""
    setattr(func, "__odss-callback__", True)
    return func


def is_callback(func: t.Callable[..., t.Any]) -> bool:
    """Check if function is safe to be called in loop."""
    return getattr(func, "__odss-callback__", False) is True


class TaskRunner:
    def __init__(self, loop):
        self.loop = loop

    def create_task(self, target, *args):
        if asyncio.iscoroutine(target):
            return self.loop.create_task(target)
        elif asyncio.iscoroutinefunction(target):
            return self.loop.create_task(target(*args))
        elif is_callback(target):
            self.loop.call_soon(target, *args)
        return self.loop.run_in_executor(None, target, *args)

    async def collect_tasks(self, targets):
        tasks = [self.create_task(method, *args) for method, *args in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.exception("Error calling a target(%s)", targets[i])
