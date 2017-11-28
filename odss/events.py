import logging

from odss_common import OBJECTCLASS
from .query import create_query
from .errors import BundleException


logger = logging.getLogger(__name__)


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

    __slots__ = ('__kind', '__bundle', '__origin')

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
        return "BundleEvent(kind={}, bundle{})".format(self.__kind, self.__bundle)


class ServiceEvent:

    ''' Service has been registered '''
    REGISTERED = 1

    ''' Properties of a registered service have been modified '''
    MODIFIED = 2

    ''' Service is in the process of being unregistered '''
    UNREGISTERING = 4

    '''
    Properties of a registered service have been modified and the new
    properties no longer match the listener's filter
    '''
    MODIFIED_ENDMATCH = 8

    __slots__ = ('__kind', '__reference', '__properties')

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
        return "ServiceEvent({}, {})".format(self.__kind, self.__reference)


class Listeners:
    def __init__(self, listener_method):
        self.__listeners = []
        self.__listener_method = listener_method

    def clear_listeners(self):
        self.__listeners = []

    def add_listener(self, listener):
        if listener is None or not hasattr(listener, self.__listener_method):
            msg = 'Missing method: "{}" in given listener'.format(self.__listener_method)
            raise BundleException(msg)

        if listener in self.__listeners:
            logger.warning('Already known listener "%s"', listener)
            return False

        self.__listeners.append(listener)
        return True
    
    def remove_listener(self, listener):
        if listener not in self.__listeners:
            return False
        try:
            self.__listeners.remove(listener)
            return True
        except ValueError:
            return False
    
    def fire_event(self, event):
        listeners = self.__listeners[:]
        for listener in listeners:
            method = getattr(listener, self.__listener_method)
            try:
                method(event)
            except:
                logger.exception('Error in listener')


class ServiceListeners:
    def __init__(self):
        self.__by_interface = {}
        self.__by_listeners = {}
    
    def clear(self):
        self.__by_interface = {}
        self.__by_listeners = {}

    def remove_listener(self, listener):
        try:
            data = self.__by_listeners.pop(listener)
            listener, interface, query = data 
            listeners = self.__by_interface[interface]
            listeners.remove(data)
            if not listeners:
                del self.__by_interface[interface]
            return True
        except KeyError:
            return False

    def add_listener(self, listener, interface=None, filter=None):
        
        if listener is None or not hasattr(listener, 'service_changed'):
            raise BundleException('Missing method: "service_changed" in given service listener')

        if listener in self.__by_listeners:
            logger.warning('Already known service listener "%s"', listener)
            return False

        try:
            query = create_query(filter)
        except (TypeError, ValueError) as ex:
            raise BundleException('Invalid service filter: {}'.format(ex))

        info = (listener, interface, query)
        self.__by_listeners[listener] = info
        self.__by_interface.setdefault(interface, []).append(info)
        return True

    def fire_event(self, event):
        properties = event.reference.get_properties()
        listeners = set()
        interfaces_with_none = properties[OBJECTCLASS] + [None]
        
        for interface in interfaces_with_none:
            try:
                listeners.update(self.__by_interface[interface])
            except KeyError:
                pass

        for listener, interface, query in listeners:
            if query.match(properties):
                listener.service_changed(event)
            elif event.kind == ServiceEvent.MODIFIED:
                previous = event.previous_properties
                if query.match(previous):
                    event = ServiceEvent(ServiceEvent.MODIFIED_ENDMATCH, event.reference, previous)
                    listener.service_changed(event)


class EventDispatcher:
    def __init__(self):
        self.__framework = Listeners('framework_changed')
        self.__bundle = Listeners('bundle_changed')
        self.__service = ServiceListeners()

    def clear(self):
        '''
        Remove all listeners
        '''
        self.__frameworks.clear()
        self.__bundles.clear()
        self.__services.clear()

    def add_bundle_listener(self, listener):
        return self.__bundle.add_listener(listener)

    def add_framework_listener(self, listener):
        return self.__framework.add_listener(listener)

    def add_service_listener(self, listener, interface=None, query_filter=None):
        return self.__service.add_listener(listener, interface, query_filter)
    
    def remove_bundle_listener(self, listener):
        return self.__bundle.remove_listener(listener)

    def remove_framework_listener(self, listener):
        return self.__framework.remove_listener(listener)
    
    def remove_service_listener(self, listener):
        return self.__service.remove_listener(listener)

    def fire_bundle_event(self, event):
        self.__bundle.fire_event(event)

    def fire_framework_stopping(self, event):
        self.__framework.fire_event(event)
        
    def fire_service_event(self, event):
        self.__service.fire_event(event)