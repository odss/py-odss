import pytest

from . import create_framework


@pytest.fixture
async def framework():
    """
    Create framework instance
    """
    try:
        framework = await create_framework()
        await framework.start()
        yield framework
    finally:
        await framework.stop()
