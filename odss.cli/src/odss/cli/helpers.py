import asyncio
import signal
import logging
import typing as t

logger = logging.getLogger(__name__)


class GracefulExit(SystemExit):
    code = 1


def register_signal_handling(framework) -> None:
    loop = asyncio.get_event_loop()

    def signal_handle(exit_code: int) -> None:
        print("catch exit singal", exit_code)
        loop.remove_signal_handler(signal.SIGTERM)
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGHUP)
        raise GracefulExit()

    try:
        loop.add_signal_handler(signal.SIGTERM, signal_handle, 0)
    except ValueError:
        logger.warning("Could not bind to SIGTERM")

    try:
        loop.add_signal_handler(signal.SIGINT, signal_handle, 0)
    except ValueError:
        logger.warning("Could not bind to SIGINT")

    try:
        loop.add_signal_handler(signal.SIGHUP, signal_handle, 100)
    except ValueError:
        logger.warning("Could not bind to SIGHUP")

    try:
        loop.add_signal_handler(signal.SIGALRM, signal_handle, 100)
    except ValueError:
        logger.warning("Could not bind to SIGHUP")


def cancel_tasks(
    tasks_to_cancel: t.Set[asyncio.Task[t.Any]], loop: asyncio.AbstractEventLoop
):
    if not tasks_to_cancel:
        return

    for task in tasks_to_cancel:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*tasks_to_cancel, return_exceptions=True))
    for task in tasks_to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            asyncio.call_exception_handler(
                {
                    "message": "Unhandled exception during asyncio.run() shutdown",
                    "exception": task.exception(),
                    "task": task,
                }
            )
