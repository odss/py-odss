import pytest_asyncio

from odss.core.events import EventDispatcher
from odss.core.loop import TaskRunner
from tests.utils import AllListener, ServiceListener


@pytest_asyncio.fixture
def listener():
    """
    Create mix listener
    """
    return AllListener()


def service_listener():
    return ServiceListener()


# @pytest.fixture()
# async def framework():
#     """
#     Create framework instance
#     """
#     framework = await create_framework()
#     await framework.start()
#     yield framework
#     await framework.stop()


@pytest_asyncio.fixture
async def events():
    """
    Create EventDispatcher instance
    """
    runner = TaskRunner()
    events = EventDispatcher(runner)
    await runner.open()
    yield events
    await runner.close()
