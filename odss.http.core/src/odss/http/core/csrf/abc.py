import abc


class IStorage(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def get_secret(self, request) -> bytes | None:
        pass  # pragma: no cover

    @abc.abstractmethod
    async def save_secret(self, response, token: bytes):
        pass  # pragma: no cover


class IPolicy(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def get_token(self, request) -> bytes | None:
        pass  # pragma: no cover
