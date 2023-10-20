import pytest_asyncio
from aiohttp.test_utils import BaseTestServer, TestClient
from yarl import URL

from .engine import ServerEngineFactory
from .server import HttpServer


class TestServer(BaseTestServer):
    def __init__(self, server) -> None:
        super().__init__(scheme="http", host=server.host, port=server.port)
        self.server = server
        self._root = URL(f"{self.scheme}://{self.host}:{self.port}")

    def _make_runner(self):
        pass

    def bind_handler(self, route):
        self.server.bind_handler(route)


@pytest_asyncio.fixture
async def http_server(unused_tcp_port):
    """
    Create http server instance
    """
    server = HttpServer(ServerEngineFactory(), "127.0.0.1", unused_tcp_port)
    await server.open()
    yield server
    await server.close()


@pytest_asyncio.fixture
async def http_client(http_server):
    client = TestClient(TestServer(http_server))
    yield client
    await client.close()
