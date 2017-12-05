import pytest

from odss.errors import BundleException
from odss.events import BundleEvent, FrameworkEvent, ServiceEvent
from odss.registry import ServiceReference
from odss_common import OBJECTCLASS, SERVICE_ID
from tests.utils import SIMPLE_BUNLE, TRANSLATE_BUNDLE


def test_add_incorrect_bundle_listener(events):
    class Listener:
        pass
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


@pytest.mark.asyncio
async def test_framework_events(framework, listener):
    context = framework.get_context()
    context.add_framework_listener(listener)

    await framework.start()
    await framework.stop()

    events = listener.events
    assert len(events) == 4
    assert events[0].kind == FrameworkEvent.STARTING
    assert events[1].kind == FrameworkEvent.STARTED
    assert events[2].kind == FrameworkEvent.STOPPING
    assert events[3].kind == FrameworkEvent.STOPPED


@pytest.mark.asyncio
@pytest.mark.usefixtures("active")
async def test_bundle_events(framework, listener):
    context = framework.get_context()
    context.add_bundle_listener(listener)

    events = listener.events

    bundle = await framework.install_bundle(SIMPLE_BUNLE)

    assert events[0].kind == FrameworkEvent.INSTALLED

    await bundle.start()

    assert events[1].kind == FrameworkEvent.STARTING
    assert events[2].kind == FrameworkEvent.STARTED

    await bundle.stop()

    assert events[3].kind == FrameworkEvent.STOPPING
    assert events[4].kind == FrameworkEvent.STOPPED

    await framework.uninstall_bundle(bundle)

    assert events[5].kind == FrameworkEvent.UNINSTALLED

    assert len(events) == 6


@pytest.mark.asyncio
@pytest.mark.usefixtures("active")
async def test_service_events(framework, listener):
    context = framework.get_context()
    context.add_service_listener(listener)

    events = listener.events

    bundle = await framework.install_bundle(TRANSLATE_BUNDLE)
    
    await bundle.start()
    assert events[0].kind == ServiceEvent.REGISTERED
    
    await bundle.stop()
    assert events[1].kind == ServiceEvent.UNREGISTERING

    await framework.uninstall_bundle(bundle)

    assert len(events) == 2

    context.remove_service_listener(listener)
    await bundle.start()
    await bundle.stop()
    assert len(events) == 2
