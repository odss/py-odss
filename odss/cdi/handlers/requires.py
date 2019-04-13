import typing as t

from odss.core.bundle import BundleContext
from odss.core.trackers import ServiceTracker

from ..consts import PROP_HANDLER_NAME, HANDLER_REQUIRES
from ..interfaces import IHandler, IHandlerFactory
from ..contexts import FactoryContext
from ..component import ComponentManager


class Activator:
    async def start(self, ctx: BundleContext) -> None:
        properties = {PROP_HANDLER_NAME: HANDLER_REQUIRES}
        self._registration = await ctx.register_service(
            IHandlerFactory, RequiresHandlerFactory(), properties
        )

    async def stop(self, ctx: BundleContext) -> None:
        await self._registration.unregister()
        self._registration = None


class RequiresHandlerFactory:
    def get_handlers(self, factory_context: FactoryContext) -> t.Iterable[IHandler]:
        specs = factory_context.get_handler(HANDLER_REQUIRES)
        return (RequiresHandlerService(specs),)


class RequiresHandlerService(IHandler):
    def __init__(self, specifications: t.Iterable[str]) -> None:
        self.specifications = specifications
        # print("RequiresHandlerService", specifications)
        self.trackers = []

    def setup(self, component: ComponentManager):
        bundle_context = component.get_bundle_context()
        self.trackers = [
            SpecificationsTracker(bundle_context, self, specification)
            for specification in self.specifications
        ]
        self._component = component

    async def start(self):
        for tracker in self.trackers:
            await tracker.open()

    async def update(self):
        if self.is_valid():
            services = [tracker.service for tracker in self.trackers]
            self._component.set_requirements(services)
        else:
            self._component.reset_requirements()
        await self._component.check_lifecycle()

    def is_valid(self):
        for tracker in self.trackers:
            if not tracker.is_valid():
                return False
        return True


class SpecificationsTracker(ServiceTracker):
    def __init__(
        self, context: BundleContext, handler: RequiresHandlerService, specifiction: str
    ):
        super().__init__(context, specifiction)
        self.handler = handler
        self.ref = None
        self.service = None

    def is_valid(self):
        return self.service is not None

    async def on_adding_service(self, reference, service):
        # print("on_adding_service2", service)
        if self.service is None:
            self.service = service
            self.ref = reference
            await self.handler.update()

    async def on_modified_service(self, reference, service):
        pass

    async def on_removed_service(self, reference, service):
        # print("on_removed_service2", service)
        if self.service == service:
            self.service = None
            self.ref = None
            await self.handler.update()
