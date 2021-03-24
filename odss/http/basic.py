from ..core.bundle import IBundleContext
from .abc import IHttpContext
from .consts import SERVICE_HTTP_ROUTE
from .decorators import route


class Auth:
    @route.get("/users")
    def get_users(self, ctx: IHttpContext):
        return ctx.json_response([])

    @route.post("/users")
    async def create_users(self, ctx: IHttpContext):
        # data = await ctx.body()
        data = await ctx.json()
        return ctx.json_response(data)

    @route.get(r"/users/{id:\d+}", response="json")
    def get_user(self, ctx: IHttpContext, id):
        return ctx.json_response({"id": id})


class Activator:
    async def start(self, ctx: IBundleContext):
        await ctx.register_service(SERVICE_HTTP_ROUTE, Auth())
        # await ctx.register_service(SERVICE_HTTP_ROUTE, Auth())
