import pytest

from odss.core import create_framework
from odss.core.events import EventDispatcher
from tests.utils import AllListener


@pytest.fixture()
def listener():
    '''
    Create mix listener
    '''
    return AllListener()


@pytest.fixture()
@pytest.mark.asyncio
async def framework():
    '''
    Create framework instance
    '''
    return await create_framework()


@pytest.fixture
@pytest.mark.asyncio
async def active(framework):
    '''
    Make framework start / stop - active
    '''
    await framework.start()
    yield
    await framework.stop()


@pytest.fixture()
def events():
    '''
    Create EventDispatcher instance
    '''
    return EventDispatcher()
