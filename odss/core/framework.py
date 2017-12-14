import asyncio
import importlib
import logging
import sys

from odss.common import ACTIVATOR_CLASS

from .bundle import Bundle, BundleContext
from .errors import BundleException
from .events import BundleEvent, EventDispatcher, FrameworkEvent, ServiceEvent
from .registry import ServiceRegistry

logger = logging.getLogger(__name__)


class Framework(Bundle):
    def __init__(self, settings, loop=None):
        super().__init__(self, 0, 'atto.framework', sys.modules[__name__])
        self.__settings = settings
        self.__bundles = []
        self.__bundles_map = {}
        self.__next_id = 1
        self.__registry = ServiceRegistry(self)
        self.__events = EventDispatcher()

        self.__activators = {}

        contex = BundleContext(self, self, self.__events)
        self.set_context(contex)

    def get_bundle_by_id(self, bundle_id):
        if bundle_id == 0:
            return self
        if bundle_id not in self.__bundles_map:
            raise BundleException('Not found bundle id={}'.format(bundle_id))
        return self.__bundles_map[bundle_id]

    def get_bundle_by_name(self, name):
        if name == self.name:
            return self
        for bundle in self.__bundles:
            if bundle.name == name:
                return bundle
        raise BundleException('Not found bundle name={}'.format(name))

    def get_property(self, name):
        if name in self.__settings:
            return self.__settings[name]
        raise KeyError('Not found property: "{}"'.format(name))

    def get_service(self, bundle, reference):
        return self.__registry.get_service(bundle, reference)

    def unget_service(self, bundle, reference):
        return self.__registry.unget_service(bundle, reference)

    def find_service_references(self, clazz=None, query=None):
        return self.__registry.find_service_references(clazz, query)

    def find_service_reference(self, clazz=None, query=None):
        return self.__registry.find_service_reference(clazz, query)

    async def register_service(self, bundle, clazz, service, properties=None):
        if bundle is None:
            raise BundleException('Invalid registration parameter: bundle')
        if clazz is None:
            raise BundleException('Invalid registration parameter: clazz')
        if service is None:
            raise BundleException('Invalid registration parameter: service')

        properties = properties.copy() if isinstance(properties, dict) else {}

        registration = self.__registry.register(
            bundle, clazz, service, properties)

        await self.__fire_service_event(
            ServiceEvent.REGISTERED, registration.get_reference()
        )
        return registration

    async def unregister_service(self, registration):
        reference = registration.get_reference()
        await self.__unregister_service(reference)

    async def __unregister_service(self, reference):
        self.__registry.unregister(reference)
        event = ServiceEvent(ServiceEvent.UNREGISTERING, reference)
        await self.__events.services.fire_event(event)

    async def install_bundle(self, name, path=None):
        logger.info('Install bungle: "{}" ({})'.format(name, path))
        for bundle in self.__bundles:
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
        self.__bundles.append(bundle)
        self.__bundles_map[bundle_id] = bundle
        self.__next_id += 1

        await self.__fire_bundle_event(BundleEvent.INSTALLED, bundle)
        return bundle

    async def uninstall_bundle(self, bundle):
        if bundle in self.__bundles:
            await bundle.stop()
            bundle._set_state(Bundle.UNINSTALLED)
            await self.__fire_bundle_event(BundleEvent.UNINSTALLED, bundle)

            del self.__bundles_map[bundle.id]
            self.__bundles.remove(bundle)
            if bundle.id in self.__activators:
                del self.__activators[bundle.id]
            try:
                del sys.modules[bundle.name]
            except KeyError:
                pass

    async def start(self):
        logger.info('Start odss.framework')
        if self.state in (Bundle.STARTING, Bundle.ACTIVE):
            logger.debug('Framework already started')
            return False

        self._set_state(Bundle.STARTING)
        await self.__fire_framework_event(BundleEvent.STARTING)

        for bundle in self.__bundles:
            try:
                await self.start_bundle(bundle)
            except BundleException:
                logger.exception(
                    'Error raised while bundle starting: "%s"', bundle.name)
        self._set_state(Bundle.ACTIVE)
        await self.__fire_framework_event(BundleEvent.STARTED)

    async def stop(self):
        logger.info('Stop odss.framework')

        if self.state != Bundle.ACTIVE:
            logger.debug('Framewok not started')
            return False

        self._set_state(Bundle.STOPPING)
        await self.__fire_framework_event(BundleEvent.STOPPING)

        for bundle in self.__bundles[::-1]:
            if self.state != Bundle.ACTIVE:
                try:
                    await self.stop_bundle(bundle)
                except BundleException:
                    logger.exception(
                        'Error raised while bundle stopping %s', bundle.name)
            else:
                logger.debug('Bundle %s already stoped', bundle)

        self._set_state(Bundle.RESOLVED)
        await self.__fire_framework_event(BundleEvent.STOPPED)

    async def start_bundle(self, bundle):
        if self.state not in (Bundle.STARTING, Bundle.ACTIVE):
            return False
        if bundle.state in (Bundle.STARTING, Bundle.ACTIVE):
            return False

        previous_state = bundle.state
        context = BundleContext(self, bundle, self.__events)
        bundle.set_context(context)
        bundle._set_state(Bundle.STARTING)
        await self.__fire_bundle_event(BundleEvent.STARTING, bundle)

        try:
            start_method = self.__get_activator_method(bundle, 'start')
            if start_method:
                start_method = asyncio.coroutine(start_method)
                await start_method(bundle.get_context())
        except BundleException:
            bundle._set_state(previous_state)
            raise
        except Exception as ex:
            bundle._set_state(previous_state)
            raise BundleException(str(ex))

        bundle._set_state(Bundle.ACTIVE)
        await self.__fire_bundle_event(BundleEvent.STARTED, bundle)
        return True

    async def stop_bundle(self, bundle):
        if bundle.state != Bundle.ACTIVE:
            return False

        previous_state = bundle.state

        bundle._set_state(Bundle.STOPPING)
        await self.__fire_bundle_event(BundleEvent.STOPPING, bundle)

        try:
            method = self.__get_activator_method(bundle, 'stop')
            if method:
                stoper = asyncio.coroutine(method)
                await stoper(bundle.get_context())
        except BundleException:
            bundle._set_state(previous_state)
            raise
        except Exception as ex:
            bundle._set_state(previous_state)
            raise BundleException(str(ex))

        for reference in self.__registry.get_bundle_references(bundle):
            await self.__unregister_service(reference)

        bundle.remove_context()
        bundle._set_state(Bundle.RESOLVED)
        await self.__fire_bundle_event(BundleEvent.STOPPED, bundle)
        return True

    def __get_activator_method(self, bundle, name):
        if bundle.id not in self.__activators:
            activator = getattr(bundle.get_module(), ACTIVATOR_CLASS, None)
            instance = activator() if activator is not None else {}
            self.__activators[bundle.id] = instance
        activator = self.__activators.get(bundle.id)
        if activator is not None:
            return getattr(activator, name, None)
        return None

    async def __fire_framework_event(self, kind):
        await self.__events.framework.fire_event(FrameworkEvent(kind, self))

    async def __fire_bundle_event(self, kind, bundle):
        await self.__events.bundles.fire_event(BundleEvent(kind, bundle))

    async def __fire_service_event(self, kind, reference):
        await self.__events.services.fire_event(ServiceEvent(kind, reference))
