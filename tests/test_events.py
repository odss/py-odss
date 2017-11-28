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


def test_add_incorrect_bundle_listener():
    class Listener:
        pass
    events = EventDispatcher()
    with pytest.raises(BundleException):
        events.add_bundle_listener(Listener())


def test_fire_bundle_listener():
    class Listener:
        fired_event = None
        num = 0
        def bundle_changed(self, event):
            self.fired_event = event
            self.num += 1

    events = EventDispatcher()
    listener = Listener()
    assert events.add_bundle_listener(listener)
    assert not events.add_bundle_listener(listener)
    event = BundleEvent(BundleEvent.INSTALLED, 'bundle', 'origin')
    events.fire_bundle_event(event)
    assert listener.fired_event == event
    assert listener.num == 1
    assert event.kind == BundleEvent.INSTALLED
    assert event.bundle == 'bundle'
    assert event.origin == 'origin'

    assert events.remove_bundle_listener(listener)
    assert not events.remove_bundle_listener(listener)
    events.fire_bundle_event(event)
    assert listener.num == 1


def test_incorrect_framework_listener():
    class Listener:
        pass
    events = EventDispatcher()
    with pytest.raises(BundleException):
        events.add_framework_listener(Listener())


# def test_framework_listener():
#     class Listener:
#         num = 0
#         def framework_changed(self):
#             self.num += 1

#     events = EventDispatcher()
#     listener = Listener()
#     assert events.add_framework_listener(listener)
#     assert not events.add_framework_listener(listener)
#     events.fire_framework_event()
#     assert listener.num == 1    

#     assert events.remove_framework_listener(listener)
#     assert not events.remove_framework_listener(listener)
#     events.fire_framework_stopping()
#     assert listener.num == 1


def test_incorrect_service_listener():
    class Listener:
        pass
    events = EventDispatcher()
    with pytest.raises(BundleException):
        events.add_service_listener(Listener())


def test_service_listener_all_interfaces():
    class Listener:
        fired_event = None
        num = 0
        def service_changed(self, event):
            self.fired_event = event
            self.num += 1

    listener = Listener()
    events = EventDispatcher()
    reference = ServiceReference('bundle', {
        SERVICE_ID: 1,
        OBJECTCLASS: ['interface']
    })
    event = ServiceEvent(ServiceEvent.REGISTERED, reference)
    assert events.add_service_listener(listener)
    assert not events.add_service_listener(listener)
    events.fire_service_event(event)
    assert listener.fired_event == event
    assert listener.num == 1    

    assert events.remove_service_listener(listener)
    assert not events.remove_service_listener(listener)
    events.fire_service_event(event)
    assert listener.num == 1

