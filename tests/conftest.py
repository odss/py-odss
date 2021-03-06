import pytest

from odss.core import create_framework
from odss.core.events import EventDispatcher
from odss.core.loop import TaskRunner
from tests.utils import ServiceListener, AllListener


@pytest.fixture()
def listener():
    """
    Create mix listener
    """
    return AllListener()


def service_listener():
    return ServiceListener()


@pytest.fixture()
@pytest.mark.asyncio
async def framework():
    """
    Create framework instance
    """
    framework = await create_framework()
    await framework.start()
    yield framework
    await framework.stop()


@pytest.fixture()
def events(event_loop):
    """
    Create EventDispatcher instance
    """
    return EventDispatcher(TaskRunner(event_loop))
