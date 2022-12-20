from .trackers import ServerEngineFactoryTracker


class Activator:
    async def start(self, ctx):
        try:
            props = ctx.get_property("odss.http.core")
        except KeyError:
            props = {}

        self.sft = ServerEngineFactoryTracker(ctx, props)
        await self.sft.open()

    async def stop(self, ctx):
        await self.sft.close()
