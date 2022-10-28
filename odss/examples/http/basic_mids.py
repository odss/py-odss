import logging

from odss.core.consts import SERVICE_PRIORITY
from odss.cdi.decorators import (
    component,
    provides,
)
from satto.http.api import IHttpMiddlewareService

logger = logging.getLogger(__name__)


async def error_middleware(ctx, handler):
    print("Middleware error_middleware called")
    try:
        response = await handler(ctx)
        if response.status != 404:
            return response
        message = response.message
    except Exception as ex:
        logger.exception(ex)
        message = str(ex)
    finally:
        print("Middleware error_middleware finished")

    return ctx.json_response({"error": message})


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
            IHttpMiddlewareService, middleware3, {SERVICE_PRIORITY: 30}
        )
        await ctx.register_service(
            IHttpMiddlewareService, middleware2, {SERVICE_PRIORITY: 10}
        )
        await ctx.register_service(
            IHttpMiddlewareService, middleware1, {SERVICE_PRIORITY: 5}
        )
        await ctx.register_service(
            IHttpMiddlewareService, error_middleware, {SERVICE_PRIORITY: 1}
        )
        # await ctx.register_service(IHttpMiddlewareService, middleware1)
        # await ctx.register_service(IHttpMiddlewareService, middleware2)
        # await ctx.register_service(IHttpMiddlewareService, middleware3)


@component
@provides(IHttpMiddlewareService)
class Middleware:
    def __init_(self):
        print("Middleware")

    def __call__(self, ctx, handler):
        print("__call_2_")
        return handler(ctx)


@component
@provides(IHttpMiddlewareService)
def test_middle(ctx, handler):
    print("test_middle")
    return handler(ctx)


@component
@provides("FooBar")
class FooBar:
    def __init_(self):
        print("FooBar")

    def sign(self):
        return "Hi"
