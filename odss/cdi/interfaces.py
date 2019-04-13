import typing as t

from odss.core.bundle import BundleContext
from .contexts import FactoryContext


class IComponentManager:
    def get_bundle_context(self) -> BundleContext:
        pass

    def set_requirements(self, requirements):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def check_lifecycle(self):
        pass


class IHandler:
    async def start(self):
        pass

    async def stop(self):
        pass

    def setup(self, component: IComponentManager):
        pass

    def is_valid(self):
        return True

    async def clear(self):
        pass

    async def pre_validate(self):
        pass

    async def post_validate(self):
        pass

    async def pre_invalidate(self):
        pass

    async def post_invalidate(self):
        pass


class IHandlerFactory:
    def get_handlers(factory_context: FactoryContext) -> t.Iterable[IHandler]:
        pass
