import logging
from odss.http.common import IHttpMiddlewareService

from .csrf import CsrfMiddleware, CookieStorage, FormAndHeaderPolicy
from .trackers import ServerService

logging.getLogger("aiohttp").setLevel("WARN")


class Activator:
    async def start(self, ctx):
        try:
            props = ctx.get_property("odss.http.core")
        except KeyError:
            props = {}

        self.service = ServerService(ctx, props)
        await self.service.open()
        await ctx.register_service(
            IHttpMiddlewareService,
            CsrfMiddleware(CookieStorage(), FormAndHeaderPolicy()),
        )

    async def stop(self, ctx):
        await self.service.close()
        self.service = None
