import pytest

from odss.core.events import EventDispatcher
from tests.utils import AllListener, ServiceListener


@pytest.fixture
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


@pytest.fixture
async def events(framework):
    """
    Create EventDispatcher instance
    """
    events = EventDispatcher()
    yield events
