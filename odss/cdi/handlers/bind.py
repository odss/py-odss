import typing as t

from odss.core.bundle import BundleContext
from odss.core.trackers import ServiceTracker

from ..component import ComponentManager
from ..consts import CALLBACK_BIND, CALLBACK_UNBIND, HANDLER_BIND, PROP_HANDLER_NAME
from ..contexts import FactoryContext
from ..interfaces import IHandler, IHandlerFactory


class Activator:
    async def start(self, ctx: BundleContext) -> None:
        properties = {PROP_HANDLER_NAME: HANDLER_BIND}
        self._registration = ctx.register_service(
            IHandlerFactory, BindHandlerFactory(), properties
        )

    async def stop(self, ctx: BundleContext) -> None:
        self._registration.unregister()
        self._registration = None


class BindHandlerFactory:
    def get_handlers(self, factory_context: FactoryContext) -> t.Iterable[IHandler]:
        binds = factory_context.get_handler(HANDLER_BIND)
        return [BindHandlerService(requirement, bind) for requirement, bind in binds]


class BindHandlerService(IHandler):
    def __init__(self, requirement, binder) -> None:
        self.requirement = requirement
        self.binder = binder
        self.tracker = None

    def setup(self, component: ComponentManager):
        bundle_context = component.get_bundle_context()
        self.tracker = SpecificationsTracker(
            bundle_context, self, self.requirement.specification
        )
        self._component = component

    async def post_validate(self):
        await self.tracker.open()

    async def pre_invalidate(self):
        await self.tracker.close()

    async def bind(self, service, reference):
        method = self.binder[CALLBACK_BIND]
        await self._component.invoke(method, service, reference)

    async def unbind(self, service, reference):
        method = self.binder[CALLBACK_UNBIND]
        await self._component.invoke(method, service, reference)


class SpecificationsTracker(ServiceTracker):
    def __init__(
        self, context: BundleContext, handler: BindHandlerService, specification: str
    ):
        super().__init__(self, context, specification)
        self.handler = handler
        self.services = []

    async def on_adding_service(self, reference, service):
        await self.handler.bind(service, reference)

    async def on_modified_service(self, reference, service):
        pass

    async def on_removed_service(self, reference, service):
        await self.handler.unbind(service, reference)
