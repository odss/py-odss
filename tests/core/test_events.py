import asyncio
import pytest

from odss.core import Callback, create_framework
from odss.core.consts import (
    OBJECTCLASS,
    SERVICE_ID,
    SERVICE_BUNDLE_ID,
    SERVICE_PRIORITY,
)
from odss.core.errors import BundleException
from odss.core.events import BundleEvent, FrameworkEvent, ServiceEvent
from odss.core.registry import ServiceReference
from tests.core.interfaces import ITextService
from tests.bundles.translate import Activator as TActivator
from tests.utils import SIMPLE_BUNDLE, TRANSLATE_BUNDLE


def test_add_incorrect_bundle_listener(events):
    class Listener:
        pass

    with pytest.raises(BundleException):
        events.add_bundle_listener(Listener())


@pytest.mark.asyncio
async def test_fire_bundle_listener(events, listener):
    assert events.add_bundle_listener(listener)
    assert not events.add_bundle_listener(listener)
    event = BundleEvent(BundleEvent.INSTALLED, "bundle", "origin")
    await events.fire_bundle_event(event)
    assert listener.last_event() == event
    assert len(listener) == 1
    assert event.kind == BundleEvent.INSTALLED
    assert event.bundle == "bundle"
    assert event.origin == "origin"

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
async def test_error_in_listener(events, listener):
    class ErrorListener:
        def bundle_changed(self, event):
            raise Exception("buu")

    events.add_bundle_listener(ErrorListener())
    events.add_bundle_listener(listener)
    event = BundleEvent(BundleEvent.INSTALLED, "bundle", "origin")

    await events.fire_bundle_event(event)

    assert listener.last_event() == event
    assert len(listener.events) == 1


@pytest.mark.asyncio
async def test_framework_listener(events, listener):
    event = BundleEvent(BundleEvent.STARTING, "bundle", "origin")
    assert events.add_framework_listener(listener)
    assert not events.add_framework_listener(listener)
    await events.fire_framework_event(event)

    assert len(listener.events) == 1

    assert events.remove_framework_listener(listener)
    assert not events.remove_framework_listener(listener)
    await events.fire_framework_event(event)
    assert len(listener.events) == 1


def test_incorrect_service_listener(events):
    class Listener:
        pass

    with pytest.raises(BundleException):
        events.add_service_listener(Listener())


@pytest.mark.asyncio
async def test_service_listener_all_interfaces(events, listener):
    reference = ServiceReference("bundle", {SERVICE_ID: 1, OBJECTCLASS: ["interface"]})
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
async def test_service_listener_with_interface(framework, events, listener):
    context = framework.get_context()

    context.add_service_listener(listener, ITextService)
    reg = await context.register_service(ITextService, "mock service")
    await reg.unregister()

    assert len(listener) == 2
    assert listener.events[0].kind == ServiceEvent.REGISTERED
    assert listener.events[1].kind == ServiceEvent.UNREGISTERING


@pytest.mark.asyncio
async def test_framework_events(listener):
    framework = await create_framework()
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
async def test_bundle_events(framework, listener):
    context = framework.get_context()
    context.add_bundle_listener(listener)

    events = listener.events

    bundle = await framework.install_bundle(SIMPLE_BUNDLE)

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
async def test_service_events(event_loop, framework, listener):
    context = framework.get_context()
    context.add_service_listener(listener)

    events = listener.events

    bundle = await framework.install_bundle(TRANSLATE_BUNDLE)

    await bundle.start()

    tasks = asyncio.all_tasks(event_loop)

    assert len(events) == 1
    assert events[0].kind == ServiceEvent.REGISTERED

    await bundle.stop()

    assert len(events) == 2
    assert events[1].kind == ServiceEvent.UNREGISTERING

    await framework.uninstall_bundle(bundle)

    assert len(events) == 2
    context.remove_service_listener(listener)

    await bundle.start()
    await bundle.stop()
    assert len(events) == 2


@pytest.mark.asyncio
async def test_service_events_modified(framework, listener):
    context = framework.get_context()

    context.add_service_listener(listener, ITextService)
    reg = await context.register_service(ITextService, "mock service")

    ref = reg.get_reference()
    old_sort_value = ref.get_sort_value()

    await reg.set_properties(
        {
            "foo": "bar",
            OBJECTCLASS: "test",
            SERVICE_ID: 12345,
            SERVICE_BUNDLE_ID: 12345,
            SERVICE_PRIORITY: 12345,
        }
    )
    ref.get_sort_value() != old_sort_value
    props = ref.get_properties()
    assert props[OBJECTCLASS] != "test"
    assert props[SERVICE_ID] != 12345
    assert props[SERVICE_BUNDLE_ID] != 12345
    assert props[SERVICE_PRIORITY] == 12345

    await reg.unregister()

    # print(listener.events)
    # assert len(listener) == 3
    assert listener.events[0].kind == ServiceEvent.REGISTERED
    assert listener.events[1].kind == ServiceEvent.MODIFIED
    assert listener.events[2].kind == ServiceEvent.UNREGISTERING
