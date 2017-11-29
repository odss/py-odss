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


class FrameworkListener:
    fired_event = None
    num = 0
    def framework_changed(self, event):
        self.fired_event = event
        self.num += 1


class BundleListener:
    fired_event = None
    num = 0
    def bundle_changed(self, event):
        self.fired_event = event
        self.num += 1


class ServiceListener:
    fired_event = None
    num = 0
    def service_changed(self, event):
        self.fired_event = event
        self.num += 1


@pytest.fixture()
def framework_listener():
    return FrameworkListener()


@pytest.fixture()
def bundle_listener():
    return BundleListener()


@pytest.fixture()
def service_listener():
    return ServiceListener()


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
async def test_fire_bundle_listener(events, bundle_listener):
    assert events.add_bundle_listener(bundle_listener)
    assert not events.add_bundle_listener(bundle_listener)
    event = BundleEvent(BundleEvent.INSTALLED, 'bundle', 'origin')
    await events.fire_bundle_event(event)
    assert bundle_listener.fired_event == event
    assert bundle_listener.num == 1
    assert event.kind == BundleEvent.INSTALLED
    assert event.bundle == 'bundle'
    assert event.origin == 'origin'

    assert events.remove_bundle_listener(bundle_listener)
    assert not events.remove_bundle_listener(bundle_listener)
    await events.fire_bundle_event(event)
    assert bundle_listener.num == 1


def test_incorrect_framework_listener(events):
    class Listener:
        pass
    with pytest.raises(BundleException):
        events.add_framework_listener(Listener())


@pytest.mark.asyncio
async def test_framework_listener(events, framework_listener):
    event = BundleEvent(BundleEvent.STARTING, 'bundle', 'origin')
    assert events.add_framework_listener(framework_listener)
    assert not events.add_framework_listener(framework_listener)
    await events.fire_framework_event(event)
    assert framework_listener.num == 1    

    assert events.remove_framework_listener(framework_listener)
    assert not events.remove_framework_listener(framework_listener)
    await events.fire_framework_event(event)
    assert framework_listener.num == 1


def test_incorrect_service_listener(events):
    class Listener:
        pass
    with pytest.raises(BundleException):
        events.add_service_listener(Listener())


@pytest.mark.asyncio
async def test_service_listener_all_interfaces(events, service_listener):
    reference = ServiceReference('bundle', {
        SERVICE_ID: 1,
        OBJECTCLASS: ['interface']
    })
    event = ServiceEvent(ServiceEvent.REGISTERED, reference)
    assert events.add_service_listener(service_listener)
    assert not events.add_service_listener(service_listener)
    await events.fire_service_event(event)
    assert service_listener.fired_event == event
    assert service_listener.num == 1    

    assert events.remove_service_listener(service_listener)
    assert not events.remove_service_listener(service_listener)
    await events.fire_service_event(event)
    assert service_listener.num == 1

