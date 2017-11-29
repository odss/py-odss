import asyncio
import importlib
import logging
import sys


from odss_common import ACTIVATOR

from .bundle import Bundle, BundleContext
from .events import BundleEvent
from .errors import BundleException, FrameworkException
from .registry import ServiceReference, ServiceRegistry


logger = logging.getLogger(__name__)


class Framework(Bundle):
    def __init__(self, settings, loop=None):
        super().__init__(self, 0, 'atto.framework', sys.modules[__name__])
        self.__settings = settings
        self.__bundles = {}
        self.__next_id = 1
        self.__registry = ServiceRegistry(self)
        if loop is None:
            loop = asyncio.get_event_loop()
        self.__loop = loop


    def get_bundle_by_id(self, bundle_id):
        if bundle_id == 0:
            return self
        if bundle_id not in self.__bundles:
            raise BundleException('Not found bundle id={}'.format(bundle_id))
        return self.__bundles[bundle_id]

    def get_bundle_by_name(self, name):
        if name == self.name:
            return self
        for bundle in self.__bundles.values():
            if bundle.name == name:
                return bundle
        raise BundleException('Not found bundle name={}'.format(name))
        
    def get_property(self, name):
        if name in self.__settings:
            return self.__settings[name]
        raise KeyError('Not found property: "{}"'.format(name))

    def install_bundle(self, name, path=None):
        logger.info('Install bungle: "{}" ({})'.format(name, path))
        for bundle in self.__bundles.values():
            if bundle.name == name:
                logger.debug('Already installed bundle: "%s"', name)
                return
        
        try:
            module_ = importlib.import_module(name)
        except (ImportError, IOError, SyntaxError) as ex:
            raise BundleException(
                'Error installing bundle "{0}": {1}'.format(name, ex))
        
        bundle_id = self.__next_id
        bundle = Bundle(self, bundle_id, name, module_)
        self.__bundles[bundle_id] = bundle
        self.__next_id += 1
        return bundle

    def register_service(self, bundle, clazz, service, properties=None):
        if bundle is None:
            raise BundleException('Invalid registration parameter: bundle')
        if clazz is None:
            raise BundleException('Invalid registration parameter: clazz')
        if service is None:
            raise BundleException('Invalid registration parameter: service')

        properties = properties.copy() if isinstance(properties, dict) else {}

        registration = self.__registry.register(
            bundle, clazz, service, properties
        )
        return registration

    def start(self):
        logger.info('Start odss.framework')
        if self.state in (Bundle.STARTING, Bundle.ACTIVE):
            logger.debug('Framework already started')
            return False

        self._set_state(Bundle.STARTING)
        self._fire_bundle_event(BundleEvent.STARTING, self)

        for bundle in self.__bundles.copy().values():
            try:
                self.start_bundle(bundle)
            except BundleException:
                logger.exception('Starting bundle: "%s"', bundle.name)
        self._set_state(Bundle.ACTIVE)
        self._fire_bundle_event(BundleEvent.STARTED, self)

        
    def stop(self):
        logger.info('Stop odss.framework')
        
        if self.state != Bundle.ACTIVE:
            logger.debug('Framewok not started')
            return False

        self._set_state(Bundle.STOPPING)
        self._fire_bundle_event(BundleEvent.STOPPING, self)

        bundles = list(self.__bundles.copy().values())
        for bundle in bundles[::-1]:
            if self.state != Bundle.ACTIVE:
                try:
                    self.stop_bundle(bundle)
                except BundleException:
                    logger.exception('Stoping bundle %s', bundle.name)
            else:
                logger.debug('Bundle %s already stoped', bundle)

        self._set_state(Bundle.RESOLVED)
        self._fire_bundle_event(BundleEvent.STOPPED, self)

    def get_service_reference(self, clazz, filter=None):
        return self.__registry.find_service_reference(clazz, filter)

    def get_service_references(self, clazz, filter=None):
        return self.__registry.find_service_references(clazz, filter)

    def get_service(self, bundle, reference):
        if not isinstance(bundle, Bundle):
            raise TypeError('Expected Bundle object')
        if not isinstance(reference, ServiceReference):
            raise TypeError('Expected ServiceReference object')

        return self.__registry.get_service(bundle, reference)

    def start_bundle(self, bundle):
        if bundle.state in (Bundle.STARTING, Bundle.ACTIVE):
            return False
        
        previous_state = bundle.state
        bundle._set_state(Bundle.STARTING)
        self._fire_bundle_event(BundleEvent.STARTING, bundle)

        start_method = self.__get_activator_method(bundle, 'start')
        if start_method:
            try:
                if asyncio.iscoroutinefunction(start_method):
                    future = start_method(BundleContext(self, bundle))
                    self.__loop.run_until_complete(future)
                else:
                    start_method(BundleContext(self, bundle))
            except (FrameworkException, BundleException):
                bundle._set_state(previous_state)
                logger.exception('Error raised while starting: %s', bundle)
                raise
            except Exception as ex:
                bundle._set_state(previous_state)
                logger.exception('Error raised while starting: %s', bundle)
                raise BundleException(str(ex))
        
        bundle._set_state(Bundle.ACTIVE)
        self._fire_bundle_event(BundleEvent.STARTED, bundle)

    def stop_bundle(self, bundle):

        previous_state = bundle.state
        bundle._set_state(Bundle.STOPPING)
        self._fire_bundle_event(BundleEvent.STOPPING, bundle)

        method = self.__get_activator_method(bundle, 'stop')
        if method:
            try:
                if asyncio.iscoroutinefunction(method):
                    future = method(BundleContext(self, bundle))
                    self.__loop.run_until_complete(future)
                else:
                    method(BundleContext(self, bundle))
                self.__registry.unregister_services(bundle)
                self.__registry.unget_services(bundle)
            except (FrameworkException, BundleException):
                bundle._set_state(previous_state)
                logger.exception(
                    'Error raised while starting bundle: %s', bundle)
                raise
            except Exception as ex:
                bundle._set_state(previous_state)
                logger.exception(
                    'Error raised while starting bundle: %s', bundle)
                raise BundleException(str(
                    ex))
        bundle._set_state(Bundle.RESOLVED)
        self._fire_bundle_event(BundleEvent.STOPPED, bundle)

    def __get_activator_method(self, bundle, name):
        activator = getattr(bundle.module, ACTIVATOR, None)
        if activator:
            return getattr(activator, name, None)
        return None

    def _fire_bundle_event(self, kind, bundle):
        pass

class _States:
    def __init__(self):
        self.map = {}

    def get(self, bundle):
        return self.map.setdefault(bundle, _State())


class _State:
    def __init__(self):
        self.resolved()

    def starting(self):
        self.__value = Bundle.STARTING

    def active(self):
        self.__value = Bundle.ACTIVE
        self.commit()

    def resolved(self):
        self.__value = Bundle.RESOLVED
        self.commit()

    def stopping(self):
        self.__value = Bundle.STOPPING

    def commit(self):
        self.__state = self.__value

    def rollback(self):
        return self.__value == self.__state

    def is_active(self):
        return self.__state == Bundle.ACTIVE

    def is_resolved(self):
        return self.__state == Bundle.RESOLVED

    def is_starting(self):
        return self.__state == Bundle.STARTING
