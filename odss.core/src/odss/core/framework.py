"""
Core module for odss.

Small asyncio python framework based on OSGi
"""

import asyncio
import logging
import signal
import sys
from collections import defaultdict
import typing as t

import async_timeout
from odss.common import BundleEvent, FrameworkEvent, ServiceEvent

from .bundle import Bundle, BundleContext
from .consts import (
    ACTIVATOR_CLASS,
    BLOCK_TIMEOUT,
    BUNDLE_DEFAULT_STARTLEVEL,
    BUNDLE_STARTLEVEL_PROP,
    FRAMEWORK_DEFAULT_STARTLEVEL,
    FRAMEWORK_INACTIVE_STARTLEVEL,
    FRAMEWORK_STARTLEVEL_PROP,
)
from .errors import BundleException
from .events import EventDispatcher
from .loader import Integration, load_bundle, unload_bundle
from .loop import create_job, create_task
from .registry import ServiceRegistry

__docformat__ = "restructuredtext en"

logger = logging.getLogger(__name__)


class Framework(Bundle):
    def __init__(self, properties):
        super().__init__(self, 0, "odss.framework", Integration(sys.modules[__name__]))
        # self.loop: asyncio.events.AbstractEventLoop = asyncio.get_event_loop()
        self.__properties = properties or {}
        self.__bundles = [self]
        self.__bundles_map = {}
        self.__next_id = 1
        self.__events = EventDispatcher()
        self.__registry = ServiceRegistry(self)
        self.__activators = {}

        self._active_start_level = FRAMEWORK_INACTIVE_STARTLEVEL
        self._target_start_level = FRAMEWORK_INACTIVE_STARTLEVEL

        contex = BundleContext(self, self, self.__events)
        self.set_context(contex)
        self._start_level = 0

    def create_task(self, target, *args):
        return create_task(target, *args)

    def create_job(self, target, *args):
        return create_job(target, *args)

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

    def get_property(self, name: str, defaults: t.Any | None = None):
        if defaults:
            return self.__properties.get(name, defaults)
        return self.__properties[name]

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

    async def register_service(self, bundle, target, service, properties=None):
        if bundle is None:
            raise BundleException("Invalid registration parameter: bundle")
        if target is None:
            raise BundleException("Invalid registration parameter: target")
        if service is None:
            raise BundleException("Invalid registration parameter: service")

        properties = properties.copy() if isinstance(properties, dict) else {}

        registration = self.__registry.register(bundle, target, service, properties)
        await self._fire_service_event(
            ServiceEvent.REGISTERED, registration.get_reference()
        )
        return registration

    async def unregister_service(self, registration) -> None:
        reference = registration.get_reference()
        await self.__unregister_service(reference)

    async def __unregister_service(self, reference) -> None:
        self.__registry.unregister(reference)
        event = ServiceEvent(ServiceEvent.UNREGISTERING, reference)
        await self.__events.services.fire_event(event)

    async def install_bundle(self, name, path=None) -> Bundle:
        for bundle in self.__bundles:
            if bundle.name == name:
                logger.debug('Already installed bundle: "%s"', name)
                return bundle

        logger.info('Install bundle: "%s" (path=%s)', name, path)

        integration = await load_bundle(name, path)

        bundle_id = self.__next_id
        bundle = Bundle(self, bundle_id, name, integration)
        self.__bundles.append(bundle)
        self.__bundles_map[bundle_id] = bundle
        self.__next_id += 1

        await self._fire_bundle_event(BundleEvent.INSTALLED, bundle)
        return bundle

    async def uninstall_bundle(self, bundle: Bundle) -> None:
        if bundle in self.__bundles:
            await bundle.stop()
            bundle._set_state(Bundle.UNINSTALLED)
            await self._fire_bundle_event(BundleEvent.UNINSTALLED, bundle)

            del self.__bundles_map[bundle.id]
            self.__bundles.remove(bundle)
            if bundle.id in self.__activators:
                del self.__activators[bundle.id]
            await self.create_job(unload_bundle, bundle.name)

    def _get_initial_start_level(self) -> int:
        try:
            return int(self.get_property(FRAMEWORK_STARTLEVEL_PROP))
        except (KeyError, ValueError):
            pass
        return FRAMEWORK_DEFAULT_STARTLEVEL

    def _get_bundle_start_level(self, bundle: Bundle) -> int:
        if bundle.start_level:
            return bundle.start_level
        try:
            bundle_start_level = int(self.get_property(BUNDLE_STARTLEVEL_PROP))
        except (KeyError, ValueError):
            pass
            bundle_start_level = BUNDLE_DEFAULT_STARTLEVEL
        bundle.start_level = bundle_start_level
        return bundle_start_level

    async def start(self, attach_signals=False) -> None:
        logger.info("Start odss.framework")
        if self.state in (Bundle.STARTING, Bundle.ACTIVE):
            logger.debug("Framework already started")
            return

        self._set_state(Bundle.STARTING)
        await self._fire_framework_event(BundleEvent.STARTING)

        start_level = self._get_initial_start_level()
        await self._set_active_start_level(start_level)

        self._set_state(Bundle.ACTIVE)
        await self._fire_framework_event(BundleEvent.STARTED)

        # if attach_signals:
        #     self._stopped = asyncio.Event()
        #     await self._stopped.wait()

    async def stop(self) -> None:
        if self.state != Bundle.ACTIVE:
            return

        logger.info("Stoping odss.framework")

        self._set_state(Bundle.STOPPING)
        await self._fire_framework_event(BundleEvent.STOPPING)
        await self._set_active_start_level(0)
        self._set_state(Bundle.RESOLVED)
        await self._fire_framework_event(BundleEvent.STOPPED)

        # if hasattr(self, "_stopped"):
        #     self._stopped.set()

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
            raise ex

        for reference in self.__registry.get_bundle_references(bundle):
            await self.__unregister_service(reference)

        bundle.remove_context()
        bundle._set_state(Bundle.RESOLVED)

        await self._fire_bundle_event(BundleEvent.STOPPED, bundle)
        return True

    async def _set_active_start_level(self, requested_level: int):
        self._target_start_level = requested_level
        if self._target_start_level != self._active_start_level:
            is_down = self._target_start_level < self._active_start_level
            levels = defaultdict(list)
            bundles = [bundle for bundle in self.get_bundles() if bundle.id != 0]
            for bundle in bundles:
                bundle_level = self._get_bundle_start_level(bundle)
                levels[bundle_level].append(bundle)

            sorted_levels = sorted(levels.keys(), reverse=is_down)
            for level in sorted_levels:
                for bundle in levels[level]:
                    if is_down and level > requested_level:
                        await self.stop_bundle(bundle)
                    elif not is_down and level <= requested_level:
                        await self.start_bundle(bundle)
            self._active_start_level = self._target_start_level

    def __get_activator_method(self, bundle, name):
        if bundle.id not in self.__activators:
            activator = getattr(bundle.get_module(), ACTIVATOR_CLASS, None)
            instance = {}
            if activator:
                instance = activator()
            else:
                logger.warning("Not found activator for %s", bundle)
            self.__activators[bundle.id] = instance
        activator = self.__activators.get(bundle.id)
        if activator is not None:
            return getattr(activator, name, None)
        return None

    async def _fire_framework_event(self, kind):
        await self.__events.framework.fire_event(FrameworkEvent(kind, self))

    async def _fire_bundle_event(self, kind, bundle):
        await self.__events.bundles.fire_event(BundleEvent(kind, bundle))

    async def _fire_service_event(self, kind, reference, properties=None):
        await self.__events.services.fire_event(
            ServiceEvent(kind, reference, properties)
        )


def register_signal_handling(framework) -> None:
    loop = asyncio.get_event_loop()

    def signal_handle(exit_code: int) -> None:
        print("catch exit singal", exit_code)
        loop.remove_signal_handler(signal.SIGTERM)
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGHUP)
        asyncio.create_task(framework.stop())

    try:
        loop.add_signal_handler(signal.SIGTERM, signal_handle, 0)
    except ValueError:
        logger.warning("Could not bind to SIGTERM")

    try:
        loop.add_signal_handler(signal.SIGINT, signal_handle, 0)
    except ValueError:
        logger.warning("Could not bind to SIGINT")

    try:
        loop.add_signal_handler(signal.SIGHUP, signal_handle, 100)
    except ValueError:
        logger.warning("Could not bind to SIGHUP")
