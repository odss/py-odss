import typing as t

from odss.core.bundle import BundleContext
from odss.core.trackers import ServiceTracker

from ..component import ComponentManager
from ..consts import HANDLER_CONSTRUCTOR_REQUIRES, HANDLER_REQUIRES, PROP_HANDLER_NAME
from ..contexts import FactoryContext
from ..interfaces import IHandler, IHandlerFactory


class Activator:
    async def start(self, ctx: BundleContext) -> None:
        self._registrations = [
            ctx.register_service(
                IHandlerFactory,
                RequiresHandlerFactory(),
                {PROP_HANDLER_NAME: HANDLER_REQUIRES},
            ),
            ctx.register_service(
                IHandlerFactory,
                ConstructorRequiresHandlerFactory(),
                {PROP_HANDLER_NAME: HANDLER_CONSTRUCTOR_REQUIRES},
            ),
        ]

    async def stop(self, ctx: BundleContext) -> None:
        for registration in self._registrations:
            registration.unregister()
        self._registrations = None


class RequiresHandlerFactory:
    def get_handlers(self, factory_context: FactoryContext) -> t.Iterable[IHandler]:
        requirements = factory_context.get_handler(HANDLER_REQUIRES)
        if requirements:
            return [
                RequiresHandlerService(field, *requirement)
                for field, requirement in requirements.items()
            ]


class ConstructorRequiresHandlerFactory:
    def get_handlers(self, factory_context: FactoryContext) -> t.Iterable[IHandler]:
        requirements = factory_context.get_handler(HANDLER_CONSTRUCTOR_REQUIRES)
        if requirements:
            return (ConstructorHandlerService(requirements),)


class RequiresHandlerService(IHandler):
    def __init__(self, field: str, specifications: t.Iterable[str], query) -> None:
        self.field = field
        self.query = query
        self.specifications = specifications
        self.trackers = []

    def setup(self, component: ComponentManager):
        bundle_context = component.get_bundle_context()
        self.trackers = [
            SpecificationsTracker(bundle_context, self, specification, self.query)
            for specification in self.specifications
        ]
        self._component = component

    async def start(self):
        for tracker in self.trackers:
            await tracker.open()

    async def stop(self):
        for tracker in self.trackers:
            await tracker.close()

    async def update(self):
        await self._component.check_lifecycle()

    def pre_validate(self):
        self._component.bind(self.field, self.trackers[0].service)

    def pre_invalidate(self):
        self._component.bind(self.field, None)

    def is_valid(self):
        for tracker in self.trackers:
            if not tracker.is_valid():
                return False
        return True

    def clear(self):
        for tracker in self.trackers:
            tracker.clear()
        self.trackers = []


class ConstructorHandlerService(IHandler):
    def __init__(self, specifications: t.Iterable[str]) -> None:
        self.specifications = specifications
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

    async def stop(self):
        for tracker in self.trackers:
            await tracker.close()

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

    def clear(self):
        for tracker in self.trackers:
            tracker.clear()
        self.trackers = []


class SpecificationsTracker(ServiceTracker):
    def __init__(
        self,
        context: BundleContext,
        handler: RequiresHandlerService,
        specifiction: str,
        filter=None,
    ):
        super().__init__(self, context, specifiction, filter)
        self.handler = handler
        self.ref = None
        self.service = None

    def is_valid(self):
        return self.service is not None

    async def on_adding_service(self, reference, service):
        if self.service is None:
            self.service = service
            self.ref = reference
            await self.handler.update()

    async def on_modified_service(self, reference, service):
        pass

    async def on_removed_service(self, reference, service):
        if self.service == service:
            self.service = None
            self.ref = None
            await self.handler.update()

    def clear(self):
        self.service = None
        self.ref = None
