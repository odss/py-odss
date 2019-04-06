import collections

from .events import ServiceEvent


__all__ = ["ServiceTracker"]


class ServiceTracker:
    def __init__(self, context, interface=None, query=None, customizer=None):
        self.context = context
        self._interface = interface
        self._query = query
        customizer = customizer if customizer is not None else self
        self._tracked = Tracked(customizer)

    async def open(self):
        self.context.add_service_listener(self._tracked, self._interface, self._query)
        await self._tracked.track_initial(self._get_initial_references())

    async def close(self):
        self.context.remove_service_listener(self._tracked)
        for reference in self.get_service_references():
            await self._tracked.untrack(reference)

    async def adding_service(self, reference):
        service = self.context.get_service(reference)
        await self.on_adding_service(reference, service)
        return service

    async def modified_service(self, reference, service):
        await self.on_modified_service(reference, service)

    async def removed_service(self, reference, service):
        await self.on_removed_service(reference, service)
        self.context.unget_service(reference)

    async def on_adding_service(self, reference, service):
        pass

    async def on_modified_service(self, reference, service):
        pass

    async def on_removed_service(self, reference, service):
        pass

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
        return self.context.get_service_references(self._interface, self._query)


class Tracked:
    def __init__(self, customizer):
        self._tracked = collections.OrderedDict()
        self._customizer = customizer

    async def service_changed(self, event):
        reference = event.reference
        if event.kind in (ServiceEvent.REGISTERED, ServiceEvent.MODIFIED):
            await self.track(reference)
        elif event.kind == ServiceEvent.UNREGISTERING:
            await self.untrack(reference)

    async def track(self, reference):
        if reference in self._tracked:
            service = self._tracked[reference]
            await self._customizer.modified_service(reference, service)
        else:
            service = await self._customizer.adding_service(reference)
            if service is not None:
                self._tracked[reference] = service
                self._sort()

    async def untrack(self, reference):
        if reference in self._tracked:
            service = self._tracked[reference]
            del self._tracked[reference]
            self._sort()
            await self._customizer.removed_service(reference, service)

    async def track_initial(self, references):
        for reference in references:
            service = await self._customizer.adding_service(reference)
            if service is not None:
                self._tracked[reference] = service

    def keys(self):
        return self._tracked.keys()

    def values(self):
        return self._tracked.values()

    def items(self):
        return self._tracked.items()

    def _sort(self):
        refs = sorted(self._tracked.keys())
        self._tracked = collections.OrderedDict(
            [(ref, self._tracked[ref]) for ref in refs]
        )
        # for ref in refs:
        #     tracked[ref] = self._tracked[ref]
        # self._tracked = tracked
