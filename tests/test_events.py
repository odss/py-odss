import pytest

from odss_common import (
    OBJECTCLASS, 
    SERVICE_BUNDLE_ID, 
    SERVICE_ID,
)
from odss.events import (
    EventDispatcher, 
    BundleEvent,
    ServiceEvent,
)
from odss.registry import ServiceReference
from odss.errors import BundleException

from tests.utils import AllListener


@pytest.fixture()
def listener():
    return AllListener()


@pytest.fixture()
def events():
    return EventDispatcher()


def test_add_incorrect_bundle_listener():
    class Listener:
        pass
    events = EventDispatcher()
    with pytest.raises(BundleException):
        events.add_bundle_listener(Listener())


@pytest.mark.asyncio
async def test_fire_bundle_listener(events, listener):
    assert events.add_bundle_listener(listener)
    assert not events.add_bundle_listener(listener)
    event = BundleEvent(BundleEvent.INSTALLED, 'bundle', 'origin')
    await events.fire_bundle_event(event)
    assert listener.last_event() == event
    assert len(listener) == 1
    assert event.kind == BundleEvent.INSTALLED
    assert event.bundle == 'bundle'
    assert event.origin == 'origin'

    assert events.remove_bundle_listener(listener)
    assert not events.remove_bundle_listener(listener)
    await events.fire_bundle_event(event)
    assert len(listener) == 1


def test_incorrect_framework_listener(events):
    class Listener:
        pass
    with pytest.raises(BundleException):
        events.add_framework_listener(Listener())


@pytest.mark.asyncio
async def test_framework_listener(events, listener):
    event = BundleEvent(BundleEvent.STARTING, 'bundle', 'origin')
    assert events.add_framework_listener(listener)
    assert not events.add_framework_listener(listener)
    await events.fire_framework_event(event)
    assert len(listener) == 1    

    assert events.remove_framework_listener(listener)
    assert not events.remove_framework_listener(listener)
    await events.fire_framework_event(event)
    assert len(listener) == 1


def test_incorrect_service_listener(events):
    class Listener:
        pass
    with pytest.raises(BundleException):
        events.add_service_listener(Listener())


@pytest.mark.asyncio
async def test_service_listener_all_interfaces(events, listener):
    reference = ServiceReference('bundle', {
        SERVICE_ID: 1,
        OBJECTCLASS: ['interface']
    })
    event = ServiceEvent(ServiceEvent.REGISTERED, reference)
    assert events.add_service_listener(listener)
    assert not events.add_service_listener(listener)
    await events.fire_service_event(event)
    assert len(listener) == 1    
    assert listener.last_event() == event

    assert events.remove_service_listener(listener)
    assert not events.remove_service_listener(listener)
    await events.fire_service_event(event)
    assert len(listener) == 1

