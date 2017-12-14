from odss.core.bundle import BundleContext
from tests.interfaces import ITextService


class NormalEchoServcie:
    def echo(self, message):
        return message[:]


class DrunkEchoServcie:
    def echo(self, message):
        return message[::-1]


class Activator:
    def __init__(self):
        self.init = True

    async def start(self, context):
        assert isinstance(context, BundleContext)
        self.context = context

        self.drunk_service = DrunkEchoServcie()
        self.normal_service = NormalEchoServcie()

        props = {'name': 'normal'}
        self.reg_normal = await context.register_service(
            ITextService, self.normal_service, props)

        props = {'name': 'drunk'}
        self.reg_drunk = await context.register_service(
            ITextService, self.drunk_service, props)

    async def stop(self, context):
        assert isinstance(context, BundleContext)
        await self.reg_normal.unregister()
        await self.reg_drunk.unregister()
        self.normal_service = None
        self.drunk_service = None
        self.context = None
