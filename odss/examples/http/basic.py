from odss.core.bundle import IBundleContext
from odss.cdi.decorators import (
    component,
    provides,
)
from satto.http.api import get, post, IHttpContext, IHttpRouteService, route

@component
@provides(IHttpRouteService)
class AuthEndpoint:
    def __init__(self, foobar: 'FooBar'):
        print('__init__', foobar)

    @get("/users")
    def get_users(self, ctx: IHttpContext):
        return ctx.json_response([])

    @post("/users")
    async def create_users(self, ctx: IHttpContext):
        # data = await ctx.body()
        data = await ctx.json()
        return ctx.json_response(data)

    @get(r"/users/{id:\d+}", response="json")
    def get_user(self, ctx: IHttpContext, id: str):
        return {"id": id}


class Activator:
    async def start(self, ctx: IBundleContext):
        pass
        # ctx.register_service(IHttpRouteService, Auth())
        # await ctx.register_service(IHttpRouteService, Auth())
