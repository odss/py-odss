import typing as t
from pathlib import Path
import json
import os
from aiofiles import os as aos, open as aopen

listdir = aos.wrap(os.listdir)


from odss.common import (
    IConfigurationStorage,
    TProperties,
)


class MemoryStorage(IConfigurationStorage):
    def __init__(self):
        self.data = {}

    async def store(self, pid: str, properties: TProperties):
        self.data[pid] = properties

    async def load(self, pid: str) -> t.Optional[TProperties]:
        return self.data.get(pid)

    async def remove(self, pid: str) -> None:
        try:
            del self.data[pid]
        except KeyError:
            return False
        return True

    async def exists(self, pid: str) -> bool:
        return pid in self.data

    async def get_pids(self) -> t.Iterable[str]:
        return list(self.data.keys())


class JsonFileStorage(IConfigurationStorage):
    def __init__(self, config_path: Path = None):
        if config_path is None:
            config_path = Path.cwd() / "conf"
        self._config_path = config_path

    async def open(self):
        if not await aos.path.exists(self._config_path):
            await aos.makedirs(self._config_path)

    async def store(self, pid: str, properties: TProperties):
        """
        Save properties from store
        """
        data = json.dumps(properties, indent="  ")
        async with aopen(self._get_file(pid), mode="w") as f:
            await f.write(data)

    async def load(self, pid: str) -> t.Optional[TProperties]:
        """
        Load properties from store
        """
        async with aopen(self._get_file(pid), mode="r") as f:
            data = await f.read()
            return json.loads(data)

    async def remove(self, pid: str) -> bool:
        """
        Remove properties from store
        """
        await aos.remove(self._get_file(pid))

    async def exists(self, pid: str) -> bool:
        """
        Check exists properties in store
        """
        return await aos.path.exists(self._get_file(pid))

    async def get_pids(self) -> t.Iterable[str]:
        """
        Return all pids from store
        """
        pids = []
        files = await listdir(self._config_path)
        for file in files:
            try:
                index = file.index(".config.json")
                pids.append(file[:index])
            except IndexError:
                pass
        return pids

    def _get_file(self, pid: str):
        return self._config_path / f"{pid}.config.json"
