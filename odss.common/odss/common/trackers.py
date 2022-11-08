import asyncio
import collections
import logging

from .core import IServiceTrackerListener
from .events import ServiceEvent

__all__ = ["ServiceTracker"]


logger = logging.getLogger(__name__)


class ServiceTracker:
    def __init__(
        self, listener: IServiceTrackerListener, context, interface=None, query=None
    ):
        self._context = context
        self._interface = interface
        self._query = query
        listener = listener if listener is not None else self
        self._tracked = _ServiceTracked(context, listener)

    async def open(self):
        logger.debug(f"Start tracking service: {self._interface} query={self._query}")
        self._context.add_service_listener(self._tracked, self._interface, self._query)
        await self._tracked.track_initial(self._get_initial_references())

    async def close(self):
        logger.debug(f"Stop tracking service: {self._interface} query={self._query}")
        self._context.remove_service_listener(self._tracked)
        for reference in self.get_service_references():
            await self._tracked.untrack(reference)

    def get_service_references(self):
        return sorted(self._tracked.keys())

    def get_service_reference(self):
        references = self.get_service_references()
        if references:
            return references[0]
        return None

    def get_services(self):
        return self._tracked.values()

    def get_service(self):
        services = list(self.get_services())
        if services:
            return services[0]
        return None

    def _get_initial_references(self):
        return self._context.get_service_references(self._interface, self._query)


class _ServiceTracked:
    def __init__(self, context, listener):
        self.context = context
        self.tracked = collections.OrderedDict()
        self.listener = listener

    async def service_changed(self, event):
        reference = event.reference
        if event.kind in (ServiceEvent.REGISTERED, ServiceEvent.MODIFIED):
            await self.track(reference)
        elif event.kind == ServiceEvent.UNREGISTERING:
            await self.untrack(reference)

    async def track(self, reference):
        logger.debug(f"Track service reference: {reference}")
        if reference in self.tracked:
            service = self.tracked[reference]
            await self.modified_service(reference, service)
        else:
            service = await self.adding_service(reference)
            if service is not None:
                self.tracked[reference] = service
                self._sort()

    async def untrack(self, reference):
        if reference in self.tracked:
            logger.debug(f"Untrack service reference: {reference}")
            service = self.tracked[reference]
            del self.tracked[reference]
            self._sort()
            await self.removed_service(reference, service)

    async def track_initial(self, references):
        for reference in references:
            service = await self.adding_service(reference)
            if service is not None:
                logger.debug(f"Track service reference: {reference}")
                self.tracked[reference] = service

    async def adding_service(self, reference):
        service = self.context.get_service(reference)
        result = self.listener.on_adding_service(reference, service)
        if asyncio.iscoroutine(result):
            await result
        return service

    async def modified_service(self, reference, service):
        result = self.listener.on_modified_service(reference, service)
        if asyncio.iscoroutine(result):
            await result

    async def removed_service(self, reference, service):
        result = self.listener.on_removed_service(reference, service)
        if asyncio.iscoroutine(result):
            await result

        self.context.unget_service(reference)

    def keys(self):
        return self.tracked.keys()

    def values(self):
        return self.tracked.values()

    def items(self):
        return self.tracked.items()

    def _sort(self):
        refs = sorted(self.tracked.keys())
        self.tracked = collections.OrderedDict(
            [(ref, self.tracked[ref]) for ref in refs]
        )
