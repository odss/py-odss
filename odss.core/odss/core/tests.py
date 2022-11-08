import pytest_asyncio

from . import create_framework


@pytest_asyncio.fixture
async def framework():
    """
    Create framework instance
    """
    framework = await create_framework()
    await framework.start()
    yield framework
    await framework.stop()
