from odss.bundle import BundleContext
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

    def start(self, context):
        assert isinstance(context, BundleContext)
        self.context = context

        self.drunk_service = DrunkEchoServcie()
        self.normal_service = NormalEchoServcie()

        props = {'name': 'normal'}
        self.reg_normal = context.register_service(
            ITextService, self.normal_service, props)

        props = {'name': 'drunk'}
        self.reg_drunk = context.register_service(
            ITextService, self.drunk_service, props)

    def stop(self, context):
        assert isinstance(context, BundleContext)
        self.reg_normal.unregister()
        self.reg_drunk.unregister()
        self.normal_service = None
        self.drunk_service = None
        self.context = None
