import typing as t

from .interfaces import (
    IConfigurationStorage,
    TProperties,
)


class MemoryStorage(IConfigurationStorage):
    def __init__(self):
        self.data = {}

    async def save(self, pid: str, properties: TProperties):
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


class _JsonFileStorage(IConfigurationStorage):
    async def save(self, pid: str, properties: TProperties):
        """
        Save properties from store
        """

    async def load(self, pid: str) -> t.Optional[TProperties]:
        """
        Load properties from store
        """

    async def remove(self, pid: str) -> bool:
        """
        Remove properties from store
        """

    async def exists(self, pid: str) -> bool:
        """
        Check exists properties in store
        """

    async def get_pids(self) -> t.Iterable[str]:
        """
        Return all pids in store
        """
