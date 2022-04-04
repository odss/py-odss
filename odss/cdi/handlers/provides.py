import typing as t

from odss.core.bundle import BundleContext

from ..component import ComponentManager
from ..consts import HANDLER_PROVIDES, PROP_HANDLER_NAME
from ..contexts import FactoryContext
from ..interfaces import IHandler, IHandlerFactory


class Activator:
    def start(self, ctx: BundleContext) -> None:
        properties = {PROP_HANDLER_NAME: HANDLER_PROVIDES}
        self._registration = ctx.register_service(
            IHandlerFactory, ProviderHandlerFactory(), properties
        )

    def stop(self, ctx: BundleContext) -> None:
        self._registration.unregister()
        self._registration = None


class ProviderHandlerFactory:
    def get_handlers(self, factory_context: FactoryContext) -> t.Iterable[IHandler]:
        specs = factory_context.get_handler(HANDLER_PROVIDES)
        return (ProviderHandlerService(specs),)


class ProviderHandlerService(IHandler):
    def __init__(self, specifications: t.Iterable[str]) -> None:
        self.specifications = specifications
        self._registration = None

    def setup(self, component: ComponentManager):
        self._component = component

    def post_validate(self):
        self._register_service()

    def pre_invalidate(self):
        self._unregister_service()

    def _register_service(self):
        if self._registration is None:
            bundle_context = self._component.get_bundle_context()
            properties = self._component.context.properties
            self._registration = bundle_context.register_service(
                self.specifications, self._component.get_instance(), properties
            )

    def _unregister_service(self):
        if self._registration is not None:
            self._registration.unregister()
            self._registration = None
