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
    has_factory_context,
)
from .interfaces import IHandlerFactory


CORE_HANDLERS = (
    "odss.cdi.handlers.bind",
    "odss.cdi.handlers.requires",
    "odss.cdi.handlers.provides",
)


class Activator:
    """
    CDI Bundle Activator
    """

    def __init__(self):
        # self._registration = None
        self.service = None
        self.bundles = []

    async def start(self, ctx: BundleContext) -> None:
        """
        The bundle has started

        :param context: The bundle context
        """

        # Create core service and run it
        self.service = CdiService(ctx)
        await self.service.open()

        # Install and start default handlers
        for handler in CORE_HANDLERS:
            bundle = await ctx.install_bundle(handler)
            await bundle.start()
            self.bundles.append(bundle)

        ctx.add_bundle_listener(self.service)

        # Manualy check current active bundles
        for bundle in ctx.get_bundles():
            if bundle.state == Bundle.ACTIVE:
                await self.service._register_bundle_factories(bundle)

    async def stop(self, ctx: BundleContext) -> None:

        ctx.remove_bundle_listener(self.service)

        await self.service.close()

        for bundle in self.bundles:
            await bundle.uninstall()
        del self.bundles[:]

        self.service = None


class CdiService:
    def __init__(self, ctx: BundleContext):
        self.__ctx = ctx
        self.__factories = {}
        self.__instances = {}
        self.__waiting_instances = {}

        self._handlers = {}
        self._handlers_refs = {}
        self._handlers_tracker = ServiceTracker(self, ctx, IHandlerFactory)

    async def open(self):
        await self._handlers_tracker.open()

    async def close(self):
        await self._handlers_tracker.close()

    async def bundle_changed(self, event: BundleEvent):
        if event.kind == BundleEvent.STARTED:
            await self._register_bundle_factories(event.bundle)
        elif event.kind == BundleEvent.STOPPING:
            await self._unregister_components_bundle(event.bundle)

    async def on_adding_service(self, reference, service):
        name = reference.get_property(PROP_HANDLER_NAME)
        if name in self._handlers:
            raise ValueError(f"Hadler: {name} already register")
        self._handlers[name] = service

        succeeded = []
        for instance_name, context in list(self.__waiting_instances.items()):
            if await self._try_setup_factory(context):
                succeeded.append(instance_name)

        for instance_name in succeeded:
            del self.__waiting_instances[instance_name]

    async def on_modified_service(self, reference, service):
        pass

    async def on_removed_service(self, reference, service):
        handler_name = reference.get_property(PROP_HANDLER_NAME)
        del self._handlers[handler_name]

        self.__ctx.unget_service(reference)
        to_remove = set()
        for factory_name in self.__factories.keys():
            factory_context = self._get_factory_context(factory_name)
            if handler_name in factory_context.get_handlers_names():
                for component in self.__instances.values():
                    if component.context.factory_context.name == factory_name:
                        to_remove.add(component)

        for component in to_remove:
            del self.__instances[component.context.name]
            await component.stop()

    def _get_handlers_factories(self, names):
        return [self._handlers[name] for name in names]

    async def _register_bundle_factories(self, bundle: Bundle):
        """
        Find and register all factories from given bundle

        :param bundle: A bundle
        """

        # Find all factories from bundle
        for factory_target, factory_context in _find_components(bundle):
            factory_name = factory_context.name
            self._valid_factory_name(factory_name)

            # Assign bundle to factory context
            factory_context.set_bundle(bundle)

            self.__factories[factory_name] = factory_target

            for name, properties in factory_context.get_instances():
                await self._setup_factory(factory_name, name, properties)

    async def _setup_factory(
        self, factory_name: str, instance_name: str, properties=None
    ):
        self._valid_instance_name(instance_name)

        factory_target = self.__factories[factory_name]
        factory_context = self._get_factory_context(factory_name)

        context = ComponentContext(
            instance_name, factory_target, factory_context, properties
        )
        success = await self._try_setup_factory(context)
        if not success:
            self.__waiting_instances[instance_name] = context

    async def _try_setup_factory(self, context: ComponentContext):
        factory_context = context.factory_context
        handlers_names = factory_context.get_handlers_names()
        try:
            handlers_factories = self._get_handlers_factories(handlers_names)
        except KeyError as ex:
            print(f"Missing: {handlers_names}")
            return False

        all_handlers = []
        for handler_factory in handlers_factories:
            handlers = handler_factory.get_handlers(factory_context)
            if handlers:
                all_handlers.extend(handlers)

        component_manager = ComponentManager(context, all_handlers)

        for handler in all_handlers:
            handler.setup(component_manager)

        self.__instances[context.name] = component_manager

        await component_manager.start()
        return True

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

    async def _unregister_components_bundle(self, bundle: Bundle) -> None:
        factories_to_remove = []
        for factory_name in self.__factories.keys():
            factory_context = self._get_factory_context(factory_name)
            if factory_context.get_bundle() is bundle:
                factories_to_remove.append(factory_name)

        for factory_name in factories_to_remove:
            await self.unregister_factory(factory_name)

    def _get_factory_context(self, factory_name: str) -> FactoryContext:
        try:
            factory = self.__factories[factory_name]
            if not has_factory_context(factory):
                raise TypeError(f"Factory context missing: {factory_name}")
            return get_factory_context(factory)

        except KeyError:
            raise TypeError(f"Unknown factory: {factory_name}")

    async def unregister_factory(self, factory_name: str) -> None:
        self.__factories.pop(factory_name)

        to_remove = self._get_instances_by_factory_name(factory_name)
        for instance_name in to_remove:
            instance = self.__instances.pop(instance_name)
            await instance.stop()

        # Remove waiting instances
        names = [
            name
            for name, instance in self.__waiting_instances.items()
            if instance.context.factory_context.name == factory_name
        ]
        for name in names:
            del self.__waiting_instances[name]

    def _get_instances_by_factory_name(self, factory_name: str) -> None:
        instances = []
        for instance_name, instance in self.__instances.items():
            if instance.context.factory_context.name == factory_name:
                instances.append(instance_name)
        return instances

    async def _unregister_all_factories(self):
        factories = list(self.__factories.keys())
        for factory_name in factories:
            await self.unregister_factory(factory_name)


def _find_components(bundle: Bundle):
    module = bundle.get_module()
    for name in dir(module):
        factory_target = getattr(module, name)
        if not inspect.isclass(factory_target) and not inspect.isroutine(
            factory_target
        ):
            continue

        # Import only elements from this module
        if sys.modules[factory_target.__module__] is not module:
            continue

        if has_factory_context(factory_target):
            factory_context = get_factory_context(factory_target)
            yield factory_target, factory_context
