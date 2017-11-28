import asyncio
import importlib
import logging
import sys


from odss_common import ACTIVATOR

from .bundle import Bundle, BundleContext
from .errors import BundleException, FrameworkException
from .registry import ServiceReference, ServiceRegistry


logger = logging.getLogger(__name__)


class Framework(Bundle):
    def __init__(self, settings):
        super().__init__(self, 0, 'atto.framework', sys.modules[__name__])
        self.__settings = settings
        self.__bundles = {}
        self.__states = _States()
        self.__next_id = 1
        self.__registry = ServiceRegistry(self)

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
        except (ImportError, IOError) as ex:
            raise BundleException(
                'Error installing bundle "{0}": {1}'.format(name, ex))
        bundle_id = self.__next_id
        bundle = Bundle(self, bundle_id, name, module_)
        self.__bundles[bundle_id] = bundle
        self.__next_id += 1

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

    async def start(self):
        logger.info('Start atto')
        state = self.__states.get(self)
        if state.is_starting() or state.is_active():
            logger.debug('Framewok already started')
            return False

        state.starting()
        for bundle in self.__bundles.copy().values():
            try:
                await self._start_bundle(bundle)
            except BundleException:
                logger.exception('Starting bundle: "%s"', bundle.name)
        state.active()

    async def stop(self):
        logger.info('Stop atto')
        state = self.__states.get(self)

        if not state.is_active():
            logger.debug('Framewok not started')
            return False
        state.stopping()
        bundles = list(self.__bundles.copy().values())
        for bundle in bundles[::-1]:
            if self.__states.get(bundle).is_active():
                try:
                    await self._stop_bundle(bundle)
                except BundleException:
                    logger.exception('Stoping bundle: "%s"', bundle.name)
            else:
                logger.debug('Bundle "%s" already stoped', bundle)

        state.resolved()

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

    async def _start_bundle(self, bundle):
        state = self.__states.get(bundle)

        state.starting()

        start_method = self.__get_activator_method(bundle, 'start')
        if start_method:
            try:
                if asyncio.iscoroutinefunction(start_method):
                    await start_method(BundleContext(self, bundle))
                else:
                    start_method(BundleContext(self, bundle))
            except (FrameworkException, BundleException):
                state.rollback()
                logger.exception('Error raised while starting: %s', bundle)
                raise
            except Exception as ex:
                state.rollback()
                logger.exception('Error raised while starting: %s', bundle)
                raise BundleException(str(ex))
        state.active()

    async def _stop_bundle(self, bundle):
        state = self.__states.get(bundle)
        state.stopping()
        method = self.__get_activator_method(bundle, 'stop')
        if method:
            try:
                if asyncio.iscoroutinefunction(method):
                    await method(BundleContext(self, bundle))
                else:
                    method(BundleContext(self, bundle))
                self.__registry.unregister_services(bundle)
                self.__registry.unget_services(bundle)
            except (FrameworkException, BundleException):
                state.rollback()
                logger.exception(
                    'Error raised while starting bundle: %s', bundle)
                raise
            except Exception as ex:
                state.rollback()
                logger.exception(
                    'Error raised while starting bundle: %s', bundle)
                raise BundleException(str(ex))

        state.resolved()

    def __get_activator_method(self, bundle, name):
        activator = getattr(bundle.module, ACTIVATOR, None)
        if activator:
            return getattr(activator, name, None)
        return None


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
