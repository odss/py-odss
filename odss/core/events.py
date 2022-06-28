import asyncio
import logging

from .consts import OBJECTCLASS
from .errors import BundleException
from .query import create_query
from .utils import class_name

logger = logging.getLogger(__name__)


BUNDLE_EVENTS = {
    1: 'INSTALLED',
    2: 'STARTED',
    4: 'STOPPED',
    8: 'UPDATED',
    10: 'UNINSTALLED',
    20: 'RESOLVED',
    40: 'UNRESOLVED',
    80: 'STARTING',
    100: 'STOPPING'
}

class BundleEvent:

    # Bundle has been installed.
    INSTALLED = 1

    # Bundle has been started.
    STARTED = 2

    # Bundle has been stopped.
    STOPPED = 4

    # Bundle has been updated.
    UPDATED = 8

    # Bundle has been uninstalled.
    UNINSTALLED = 10

    # Bundle has been resolved.
    RESOLVED = 20

    # Bundle has been unresolved.
    UNRESOLVED = 40

    # Bundle is about to be activated.
    STARTING = 80

    # Bundle is about to deactivated.
    STOPPING = 100

    __slots__ = ("__kind", "__bundle", "__origin")

    def __init__(self, kind, bundle, origin=None):
        self.__kind = kind
        self.__bundle = bundle
        self.__origin = origin

    @property
    def kind(self):
        return self.__kind

    @property
    def bundle(self):
        return self.__bundle

    @property
    def origin(self):
        return self.__origin

    def __str__(self):
        return "BundleEvent(kind={}, bundle={})".format(BUNDLE_EVENTS[self.__kind], self.__bundle)


class FrameworkEvent(BundleEvent):
    pass

SERVICE_EVENTS = {
    1: "REGISTERED",
    2: "MODIFIED",
    4: "UNREGISTERING",
    8: "MODIFIED_ENDMATCH"
}
class ServiceEvent:

    """Service has been registered"""

    REGISTERED = 1

    """ Properties of a registered service have been modified """
    MODIFIED = 2

    """ Service is in the process of being unregistered """
    UNREGISTERING = 4

    """
    Properties of a registered service have been modified and the new
    properties no longer match the listener's filter
    """
    MODIFIED_ENDMATCH = 8

    __slots__ = ("__kind", "__reference", "__properties")

    def __init__(self, kind_, reference, properties=None):
        self.__kind = kind_
        self.__reference = reference
        if properties is None or not isinstance(properties, dict):
            properties = {}
        self.__properties = properties

    @property
    def kind(self):
        return self.__kind

    @property
    def reference(self):
        return self.__reference

    @property
    def previous_properties(self):
        return self.__properties.copy()

    def __str__(self):
        return "ServiceEvent({}, {})".format(SERVICE_EVENTS[self.__kind], self.__reference)

class Listeners:
    def __init__(self, runner, listener_method):
        super().__init__()
        self.listeners = []
        self.listener_method = listener_method
        self.runner = runner

    def clear_listeners(self):
        self.listeners = []

    def add_listener(self, listener):
        if listener is None or not hasattr(listener, self.listener_method):
            msg = 'Missing method: "{}" in given listener'.format(self.listener_method)
            raise BundleException(msg)

        if listener in self.listeners:
            logger.info('Already known listener "%s"', listener)
            return False

        self.listeners.append(listener)
        return True

    def remove_listener(self, listener):
        if listener not in self.listeners:
            return False
        try:
            self.listeners.remove(listener)
            return True
        except ValueError:
            return False

    async def fire_event(self, event):
        methods = [getattr(listener, self.listener_method) for listener in self.listeners]
        tasks = [self.runner.create_task(method, event) for method in methods]
        await self.runner.wait_for_tasks(tasks)

class ServiceListeners:
    def __init__(self, runner):
        super().__init__()
        self.by_interface = {}
        self.by_listeners = {}
        self.runner = runner

    def clear(self):
        self.by_interface = {}
        self.by_listeners = {}

    def remove_listener(self, listener):
        try:
            data = self.by_listeners.pop(listener)
            listener, interface, query = data
            listeners = self.by_interface[interface]
            listeners.remove(data)
            if not listeners:
                del self.by_interface[interface]
            return True
        except KeyError:
            return False

    def add_listener(self, listener, interface=None, query=None):
        if listener is None or not hasattr(listener, "service_changed"):
            raise BundleException(
                'Missing method: "service_changed" in given service listener'
            )
        if interface is not None:
            interface = class_name(interface)
        if listener in self.by_listeners:
            logger.info('Already known service listener "%s"', listener)
            return False

        try:
            query = create_query(query)
        except (TypeError, ValueError) as ex:
            raise BundleException("Invalid service query: {}".format(ex))

        info = (listener, interface, query)
        self.by_listeners[listener] = info
        self.by_interface.setdefault(interface, []).append(info)
        return True

    def fire_event(self, event):
        properties = event.reference.get_properties()
        listeners = set()
        interfaces_with_none = tuple(properties[OBJECTCLASS]) + (None,)

        for interface in interfaces_with_none:
            try:
                listeners.update(self.by_interface[interface])
            except KeyError:
                pass

        tasks = []
        for listener, interface, query in listeners:
            method = listener.service_changed
            if query.match(properties):
                self.runner.enqueue_task(method, event)
            elif event.kind == ServiceEvent.MODIFIED:
                previous = event.previous_properties
                if query.match(previous):
                    event = ServiceEvent(
                        ServiceEvent.MODIFIED_ENDMATCH, event.reference, previous
                    )
                    self.runner.enqueue_task(method, event)

class EventDispatcher:
    def __init__(self, runner):
        self.runner = runner
        self.framework = Listeners(self.runner, "framework_changed")
        self.bundles = Listeners(self.runner, "bundle_changed")
        self.services = ServiceListeners(self.runner)

    def clear(self):
        """
        Remove all listeners
        """
        self.framework.clear()
        self.bundles.clear()
        self.services.clear()

    def add_bundle_listener(self, listener):
        return self.bundles.add_listener(listener)

    def add_framework_listener(self, listener):
        return self.framework.add_listener(listener)

    def add_service_listener(self, listener, interface=None, filter=None):
        return self.services.add_listener(listener, interface, filter)

    def remove_bundle_listener(self, listener):
        return self.bundles.remove_listener(listener)

    def remove_framework_listener(self, listener):
        return self.framework.remove_listener(listener)

    def remove_service_listener(self, listener):
        return self.services.remove_listener(listener)

    async def fire_framework_event(self, event):
        await self.framework.fire_event(event)

    async def fire_bundle_event(self, event):
        await self.bundles.fire_event(event)

    def fire_service_event(self, event):
        self.services.fire_event(event)
