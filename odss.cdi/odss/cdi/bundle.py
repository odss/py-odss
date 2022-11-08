from odss.core.bundle import Bundle, BundleContext

from .service import CdiService

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
