"""
Core module for odss.

Small asyncio python framework based on OSGi
"""

import asyncio
import logging
import signal
import sys

import async_timeout

from .bundle import Bundle, BundleContext, IBundle
from .consts import ACTIVATOR_CLASS, BLOCK_TIMEOUT
from .errors import BundleException
from .events import BundleEvent, EventDispatcher, FrameworkEvent, ServiceEvent
from .loader import Integration, load_bundle, unload_bundle
from .loop import TaskRunner, wait_for_tasks
from .registry import ServiceRegistry


__docformat__ = "restructuredtext en"

logger = logging.getLogger(__name__)


class Framework(Bundle):
    def __init__(self, properties):
        super().__init__(self, 0, "odss.framework", Integration(sys.modules[__name__]))
        self.loop: asyncio.events.AbstractEventLoop = asyncio.get_event_loop()
        self.__properties = properties
        self.__bundles = []
        self.__bundles_map = {}
        self.__next_id = 1
        self.__runner = TaskRunner(self.loop)
        self.__events = EventDispatcher(self.__runner)
        self.__registry = ServiceRegistry(self)

        self.__activators = {}

        contex = BundleContext(self, self, self.__events)
        self.set_context(contex)

    def create_task(self, target, *args):
        return self.__runner.create_task(target, *args)

    def create_job(self, target, *args):
        return self.__runner.create_job(target, *args)

    def get_bundles(self):
        return self.__bundles.copy()

    def get_bundle_by_id(self, bundle_id):
        if bundle_id == 0:
            return self
        if bundle_id not in self.__bundles_map:
            raise BundleException("Not found bundle id={}".format(bundle_id))
        return self.__bundles_map[bundle_id]

    def get_bundle_by_name(self, name):
        if name == self.name:
            return self
        for bundle in self.__bundles:
            if bundle.name == name:
                return bundle
        raise BundleException("Not found bundle name={}".format(name))

    def get_properties(self):
        return self.__properties.copy()

    def get_property(self, name):
        if name in self.__properties:
            return self.__properties[name]
        raise KeyError('Not found property: "{}"'.format(name))

    def get_service(self, bundle, reference):
        return self.__registry.get_service(bundle, reference)

    def unget_service(self, bundle, reference):
        return self.__registry.unget_service(bundle, reference)

    def find_service_references(self, clazz=None, query=None):
        return self.__registry.find_service_references(clazz, query)

    def find_service_reference(self, clazz=None, query=None):
        return self.__registry.find_service_reference(clazz, query)

    def get_bundle_references(self, bundle):
        return self.__registry.get_bundle_references(bundle)

    def get_bundle_using_services(self, bundle):
        return self.__registry.get_bundle_using_services(bundle)

    def register_service(self, bundle, target, service, properties=None):
        if bundle is None:
            raise BundleException("Invalid registration parameter: bundle")
        if target is None:
            raise BundleException("Invalid registration parameter: target")
        if service is None:
            raise BundleException("Invalid registration parameter: service")

        properties = properties.copy() if isinstance(properties, dict) else {}

        registration = self.__registry.register(bundle, target, service, properties)
        self._fire_service_event(ServiceEvent.REGISTERED, registration.get_reference())
        return registration

    def unregister_service(self, registration) -> None:
        reference = registration.get_reference()
        self.__unregister_service(reference)

    def __unregister_service(self, reference) -> None:
        self.__registry.unregister(reference)
        event = ServiceEvent(ServiceEvent.UNREGISTERING, reference)
        self.__events.services.fire_event(event)

    async def install_bundle(self, name, path=None) -> Bundle:
        for bundle in self.__bundles:
            if bundle.name == name:
                logger.debug('Already installed bundle: "%s"', name)
                return

        logger.info('Install bundle: "%s" (path=%s)', name, path)
        integration = await load_bundle(self.__runner, name, path)

        bundle_id = self.__next_id
        bundle = Bundle(self, bundle_id, name, integration)
        self.__bundles.append(bundle)
        self.__bundles_map[bundle_id] = bundle
        self.__next_id += 1

        await self._fire_bundle_event(BundleEvent.INSTALLED, bundle)
        return bundle

    async def uninstall_bundle(self, bundle: IBundle) -> None:
        if bundle in self.__bundles:
            await bundle.stop()
            bundle._set_state(Bundle.UNINSTALLED)
            await self._fire_bundle_event(BundleEvent.UNINSTALLED, bundle)

            del self.__bundles_map[bundle.id]
            self.__bundles.remove(bundle)
            if bundle.id in self.__activators:
                del self.__activators[bundle.id]
            await self.create_job(unload_bundle, bundle.name)

    async def start(self, attach_signals=False) -> None:
        logger.info("Start odss.framework")
        if self.state in (Bundle.STARTING, Bundle.ACTIVE):
            logger.debug("Framework already started")
            return False

        await self.__runner.open()

        self._set_state(Bundle.STARTING)
        await self._fire_framework_event(BundleEvent.STARTING)

        tasks = [
            asyncio.create_task(self.start_bundle(bundle))
            for bundle in self.__bundles.copy()
        ]
        await wait_for_tasks(tasks)

        self._set_state(Bundle.ACTIVE)
        await self._fire_framework_event(BundleEvent.STARTED)

        if attach_signals:
            self._stopped = asyncio.Event()
            register_signal_handling(self)

            await self._stopped.wait()

    async def stop(self) -> None:
        if self.state != Bundle.ACTIVE:
            return False

        logger.info("Stoping odss.framework")

        self._set_state(Bundle.STOPPING)
        await self._fire_framework_event(BundleEvent.STOPPING)
        tasks = [
            asyncio.create_task(self.stop_bundle(bundle))
            for bundle in self.__bundles[::-1]
        ]
        await wait_for_tasks(tasks)

        self._set_state(Bundle.RESOLVED)
        await self._fire_framework_event(BundleEvent.STOPPED)
        await self.__runner.close()

        if hasattr(self, "_stopped"):
            self._stopped.set()

    async def start_bundle(self, bundle):
        if self.state not in (Bundle.STARTING, Bundle.ACTIVE):
            return False

        if bundle.state in (Bundle.STARTING, Bundle.ACTIVE):
            return False

        logger.debug("Start bundle %s", bundle)
        previous_state = bundle.state
        context = BundleContext(self, bundle, self.__events)
        bundle.set_context(context)
        bundle._set_state(Bundle.STARTING)
        await self._fire_bundle_event(BundleEvent.STARTING, bundle)

        try:
            start_method = self.__get_activator_method(bundle, "start")
            if start_method:
                target = start_method(context)
                if asyncio.iscoroutine(target):
                    async with async_timeout.timeout(BLOCK_TIMEOUT):
                        await target
        except Exception as ex:
            bundle._set_state(previous_state)
            logger.warning("Problem with start bundle: {0} - {1}".format(bundle, ex))
            raise ex

        bundle._set_state(Bundle.ACTIVE)
        await self._fire_bundle_event(BundleEvent.STARTED, bundle)
        return True

    async def stop_bundle(self, bundle):
        if bundle.state != Bundle.ACTIVE:
            return False

        logger.debug("Stop bundle %s", bundle)
        previous_state = bundle.state
        bundle._set_state(Bundle.STOPPING)
        await self._fire_bundle_event(BundleEvent.STOPPING, bundle)
        try:
            stop_method = self.__get_activator_method(bundle, "stop")
            if stop_method:
                target = stop_method(bundle.get_context())
                if asyncio.iscoroutine(target):
                    async with async_timeout.timeout(BLOCK_TIMEOUT):
                        await target
        except Exception as ex:
            bundle._set_state(previous_state)
            logger.warning("Problem with stop bundle: {0} - {1}".format(bundle, ex))
            raise ex

        for reference in self.__registry.get_bundle_references(bundle):
            self.__unregister_service(reference)

        bundle.remove_context()
        bundle._set_state(Bundle.RESOLVED)

        await self._fire_bundle_event(BundleEvent.STOPPED, bundle)
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

    async def _fire_framework_event(self, kind):
        await self.__events.framework.fire_event(FrameworkEvent(kind, self))

    async def _fire_bundle_event(self, kind, bundle):
        await self.__events.bundles.fire_event(BundleEvent(kind, bundle))

    def _fire_service_event(self, kind, reference, properties=None):
        self.__events.services.fire_event(ServiceEvent(kind, reference, properties))


def register_signal_handling(framework) -> None:
    def signal_handle(exit_code: int) -> None:
        framework.loop.remove_signal_handler(signal.SIGTERM)
        framework.loop.remove_signal_handler(signal.SIGINT)
        framework.loop.remove_signal_handler(signal.SIGHUP)
        asyncio.create_task(framework.stop())

    try:
        framework.loop.add_signal_handler(signal.SIGTERM, signal_handle, 0)
    except ValueError:
        logger.warning("Could not bind to SIGTERM")

    try:
        framework.loop.add_signal_handler(signal.SIGINT, signal_handle, 0)
    except ValueError:
        logger.warning("Could not bind to SIGINT")

    try:
        framework.loop.add_signal_handler(signal.SIGHUP, signal_handle, 100)
    except ValueError:
        logger.warning("Could not bind to SIGHUP")
