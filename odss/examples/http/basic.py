from odss.core.bundle import IBundleContext
from odss.cdi.decorators import (
    component,
    provides,
)
from satto.http.api import view, get, post, IHttpContext, IHttpRouteService


# @component
# @provides(IHttpRouteService)
@view("/auth")
class AuthEndpoint:
    def __init__(self):
        print("__init__")

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
        await ctx.register_service(IHttpRouteService, AuthEndpoint(), {"scope": "auth"})
        # await ctx.register_service(IHttpRouteService, Auth())
