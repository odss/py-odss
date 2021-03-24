import logging

from aiohttp import web

from ..core.consts import SERVICE_RANKING
from .consts import SERVICE_HTTP_MIDDLEWARE

logger = logging.getLogger(__name__)


async def error_middleware(ctx, handler):
    print("Middleware error_middleware called")
    try:
        response = await handler(ctx)
        if response.status != 404:
            return response
        message = response.message
    except Exception as ex:
        logger.exception(str(ex))
        message = str(ex)
    finally:
        print("Middleware error_middleware finished")

    return web.json_response({"error": message})


async def middleware1(ctx, handler):
    print("Middleware 1 called")
    response = await handler(ctx)
    print("Middleware 1 finished")
    return response


async def middleware2(ctx, handler):
    print("Middleware 2 called")
    response = await handler(ctx)
    print("Middleware 2 finished")
    return response


async def middleware3(ctx, handler):
    print("Middleware 3 called")
    response = await handler(ctx)
    print("Middleware 3 finished")
    return response


class Activator:
    async def start(self, ctx):
        await ctx.register_service(
            SERVICE_HTTP_MIDDLEWARE, error_middleware, {SERVICE_RANKING: 1}
        )

        await ctx.register_service(
            SERVICE_HTTP_MIDDLEWARE, middleware1, {SERVICE_RANKING: 10}
        )
        await ctx.register_service(
            SERVICE_HTTP_MIDDLEWARE, middleware2, {SERVICE_RANKING: 10}
        )
        await ctx.register_service(
            SERVICE_HTTP_MIDDLEWARE, middleware3, {SERVICE_RANKING: 30}
        )

        # await ctx.register_service(SERVICE_HTTP_MIDDLEWARE, middleware1)
        # await ctx.register_service(SERVICE_HTTP_MIDDLEWARE, middleware2)
        # await ctx.register_service(SERVICE_HTTP_MIDDLEWARE, middleware3)
