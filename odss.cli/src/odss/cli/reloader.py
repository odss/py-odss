import asyncio
import logging
import sys
from pathlib import Path

import importlib

logger = logging.getLogger(__name__)


class Reloader:
    SLEEP_TIME = 1

    def __init__(self, framework) -> None:
        self.framework = framework
        self.stop_event = asyncio.Event()
        self.runner = None

    async def start(self):
        logger.info("Watching odss apps")
        if self.stop_event:
            self.runner = asyncio.create_task(self.run())

    async def stop(self):
        if self.runner:
            runner, self.runner = self.runner, None
            runner.cancel()
            await asyncio.wait_for(runner, 1)

    async def run(self):
        tick = self.ticker()
        while self.stop_event:
            try:
                result = next(tick)
                if result:
                    await self.reload_bunldes(result)
            except StopIteration:
                break
            except AttributeError as ex:
                print(ex)
            try:
                await asyncio.sleep(self.SLEEP_TIME)
            except asyncio.CancelledError:
                break

    async def reload_bunldes(self, names: list[str]) -> None:
        logger.info("Reload bundles. Modules: %s", names)
        bundles = self.framework.get_bundles()
        for name in names:
            for bundle in bundles:
                if name.startswith(bundle.name):
                    await self.framework.uninstall_bundle(bundle)
                    new_bundle = await self.framework.install_bundle(bundle.name)
                    await self.framework.start_bundle(new_bundle)
                    break
            # else:
            # importlib.reload(sys.modules[name])

    def ticker(self):
        mtimes = {}
        while True:
            updated = []
            for name, file_path, mtime in self.get_files():
                old_time = mtimes.get(file_path)
                mtimes[file_path] = mtime
                if old_time is None:
                    logger.debug("File %s first seen (mtime=%s)", file_path, mtime)
                    continue
                elif mtime > old_time:
                    logger.debug(
                        "File %s previous mtime: %s, current mtime: %s",
                        file_path,
                        old_time,
                        mtime,
                    )
                    updated.append(name)
            yield updated

    def get_files(self) -> list[tuple[str, Path, int]]:
        unique = set()
        for name, file in self.watched_files():
            if file not in unique:
                mtime = file.stat().st_mtime
                unique.add(file)
                yield name, file, mtime

    def watched_files(self) -> list[str, Path]:
        for name, module in sorted(sys.modules.items()):
            file_path = getattr(module, "__file__", None)
            if file_path and name.startswith("odss."):
                yield name, Path(file_path),
