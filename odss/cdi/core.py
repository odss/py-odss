import inspect
import sys

from odss.core.bundle import Bundle, BundleContext
from odss.core.events import BundleEvent
from odss.core.trackers import ServiceTracker

from .component import ComponentManager
from .consts import PROP_HANDLER_NAME
from .contexts import (
    ComponentContext,
    FactoryContext,
    get_factory_context,
    is_component_factory,
)
from .interfaces import IHandlerFactory

CORE_HANDLERS = (
    "odss.cdi.handlers.bind",
    "odss.cdi.handlers.requires",
    "odss.cdi.handlers.provides",
)


class Activator:
    async def start(self, ctx: BundleContext) -> None:
        self.service = CdiService(ctx)
        await self.service.open()

        for handler in CORE_HANDLERS:
            bundle = await ctx.install_bundle(handler)
            await bundle.start()

        ctx.add_bundle_listener(self.service)
        for bundle in ctx.get_bundles():
            if bundle.state == Bundle.ACTIVE:
                await self.service.register_components_bundle(bundle)

    async def stop(self, ctx: BundleContext) -> None:
        await self.service.close()


class HandlersTracker(ServiceTracker):
    def __init__(self, context: BundleContext):
        super().__init__(context, IHandlerFactory)
        self._handlers = {}

    async def on_adding_service(self, reference, service):
        # print("on_adding_service", service)
        name = reference.get_property(PROP_HANDLER_NAME)
        if name in self._handlers:
            raise NameError(name)
        self._handlers[name] = service

    async def on_modified_service(self, reference, service):
        pass

    async def on_removed_service(self, reference, service):
        # print("on_removed_service", service)
        name = reference.get_property(PROP_HANDLER_NAME)
        del self._handlers[name]

    def get_handlers(self, names):
        return [self._handlers[name] for name in names]


class CdiService:
    def __init__(self, ctx: BundleContext):
        self.ctx = ctx
        self.__factories = {}
        self.__instances = {}
        self._handlers = HandlersTracker(ctx)

    async def open(self):
        await self._handlers.open()

    async def close(self):
        await self._handlers.close()

    async def bundle_changed(self, event: BundleEvent):
        if event.kind == BundleEvent.STARTED:
            await self.register_components_bundle(event.bundle)
        elif event.kind == BundleEvent.STOPPING:
            await self.unregister_components_bundle(event.bundle)

    async def register_components_bundle(self, bundle: Bundle):
        for factory_class, factory_context in find_components(bundle):
            factory_name = factory_context.name
            self._valid_factory_name(factory_name)
            factory_context.set_bundle(bundle)
            self.__factories[factory_name] = [factory_class, factory_context]

            for name, properties in factory_context.get_instances().items():
                self._valid_instance_name(name)
                handlers = self._get_handlers(factory_context)
                context = ComponentContext(
                    name, factory_class, factory_context, properties
                )
                component_manager = ComponentManager(context, handlers)
                for handler in handlers:
                    handler.setup(component_manager)
                self.__instances[name] = component_manager
                await component_manager.start()

    def _valid_factory_name(self, factory_name: str) -> None:
        if not factory_name or not isinstance(factory_name, str):
            raise ValueError(
                "Factory name must be non-empty string. ({})".format(factory_name)
            )
        if factory_name in self.__factories:
            raise ValueError("'{0}' factory already exist".format(factory_name))

    def _valid_instance_name(self, instance_name: str) -> None:
        if instance_name in self.__instances:
            raise ValueError(
                "'{0}' is an already running instance name".format(instance_name)
            )

    async def unregister_components_bundle(self, bundle: Bundle) -> None:
        factories_to_remove = []
        for factory_name in self.__factories:
            factory_class, factory_context = self.__factories[factory_name]
            if factory_context.get_bundle() is bundle:
                factories_to_remove.append(factory_name)

        for factory_name in factories_to_remove:
            await self.unregister_factory(factory_name)

    async def unregister_factory(self, factory_name: str) -> None:
        self.__factories.pop(factory_name)
        to_remove = self._get_instances_by_factory(factory_name)
        for instance_name in to_remove:
            instance = self.__instances.pop(instance_name)
            await instance.stop()

    def _get_instances_by_factory(self, factory_name: str) -> None:
        istances = []
        for name, instance in self.__instances.items():
            if instance.context.factory_context.name == factory_name:
                istances.append(name)
        return istances

    def _get_handlers(self, factory_context: FactoryContext):
        all_handlers = []
        handlers_names = factory_context.get_handlers_names()
        handlers_factories = self._handlers.get_handlers(handlers_names)
        for handler_factory in handlers_factories:
            handlers = handler_factory.get_handlers(factory_context)
            if handlers:
                all_handlers.extend(handlers)
        return all_handlers


def find_components(bundle):
    module = bundle.get_module()
    for name in dir(module):
        factory_class = getattr(module, name)
        if not inspect.isclass(factory_class):
            continue

        # skip imported elements
        if sys.modules[factory_class.__module__] is not module:
            continue

        if is_component_factory(factory_class):
            factory_context = get_factory_context(factory_class)
            yield factory_class, factory_context
