import asyncio
import inspect
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


class TaskPool:
    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.loop_event = asyncio.Event()
        self.tasks:asyncio.Queue[tuple[t.Callable, list[t.Any]]] = asyncio.Queue()
        self.workers: list[asyncio.Task] = []

    def enqueue(self, handler, args):
        self.tasks.put_nowait((handler, args))

    async def start(self):
        if self.loop_event.is_set():
            return
        self.workers = [
            asyncio.create_task(self._run(id), name=f"Worker({id})")
            for i in range(self.max_workers)
        ]

    async def stop(self):
        if self.loop_event.is_set():
            return

        self.loop_event.set()
        for i in range(self.max_workers):
            await self.tasks.put(self.loop_event)

        await self.tasks.join()

        for worker in self.workers:
            worker.cancel()
        self.workers = []

    async def _run(self, id: int):
        while True:
            try:
                task = await self.tasks.get()
                if task == self.loop_event:
                    self.tasks.task_done()
                    break
                handler, args = task
                try:
                    result = handler(*args)
                    if asyncio.iscoroutine(result):
                        await result
                finally:
                    self.tasks.task_done()
            except asyncio.CancelledError as ex:
                break
            except Exception as ex:
                logger.exception(ex)


class TaskRunner:
    def __init__(self):
        self.task_pool = TaskPool()

    async def open(self):
        await self.task_pool.start()

    async def close(self):
        await self.task_pool.stop()

    def enqueue_task(self, handler, *args):
        self.task_pool.enqueue(handler, args)


def create_task(target, *args) -> t.Optional[asyncio.Task]:
    assert target
    if asyncio.iscoroutine(target):
        return asyncio.create_task(target)
    elif asyncio.iscoroutinefunction(target):
        return asyncio.create_task(target(*args))
    elif inspect.ismethod(target):
        asyncio.get_event_loop().call_soon(target, *args)
        return None

    raise TypeError(
        "Incorrect type of target. Excpected function, coroutine or coroutinefunction"
    )


def create_job(target, *args) -> asyncio.Future:
    return asyncio.get_event_loop().run_in_executor(None, target, *args)


def run_in_future(target, *args) -> asyncio.Future:
    future = asyncio.get_event_loop().create_future()
    try:
        future.set_result(target(*args))
    except Exception as ex:
        future.set_exception(ex)
    return future


async def wait_for_tasks(tasks: t.List[asyncio.Task]) -> None:
    start_time = monotonic()
    pending = [task for task in tasks if task and not task.done()]
    while pending:
        _, pending = await asyncio.wait(pending, timeout=BLOCK_LOG_TIMEOUT)
        wait_time = monotonic() - start_time
        for task in pending:
            logger.warning("Waited %s seconds for task: %s", wait_time, task)
