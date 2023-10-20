import logging

from odss.common import OBJECTCLASS, ServiceEvent, get_class_name

from .errors import BundleException
from .loop import create_task, wait_for_tasks
from .query import create_query

logger = logging.getLogger(__name__)


class Listeners:
    def __init__(self, listener_method):
        super().__init__()
        self.listeners = []
        self.listener_method = listener_method

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
        methods = [
            getattr(listener, self.listener_method) for listener in self.listeners
        ]
        tasks = [create_task(method, event) for method in methods]
        await wait_for_tasks(tasks)


class ServiceListeners:
    def __init__(self):
        super().__init__()
        self.by_interface = {}
        self.by_listeners = {}

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
            interface = get_class_name(interface)
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

    async def fire_event(self, event):
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
                tasks.append(create_task(method, event))
            elif event.kind == ServiceEvent.MODIFIED:
                previous = event.previous_properties
                if query.match(previous):
                    event = ServiceEvent(
                        ServiceEvent.MODIFIED_ENDMATCH, event.reference, previous
                    )
                    tasks.append(create_task(method, event))
        await wait_for_tasks(tasks)


class EventDispatcher:
    def __init__(self):
        self.framework = Listeners("framework_changed")
        self.bundles = Listeners("bundle_changed")
        self.services = ServiceListeners()

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

    async def fire_service_event(self, event):
        await self.services.fire_event(event)
