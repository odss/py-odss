from odss.bundle import BundleContext

from tests.interfaces import IEchoService


class DrunkEchoServcie:
    def echo(self, message):
        return message[::-1]  


class Activator:
    def __init__(self):
        self.init = True

    def start(self, context):
        assert isinstance(context, BundleContext)
        self.context = context
        self.service = DrunkEchoServcie()
        self.properties = {'name': 'drunk'}
        self.registration = context.register_service(IEchoService, self.service, self.properties)
    
    def stop(self, context):
        assert isinstance(context, BundleContext)
        self.registration.unregister()
        self.service = None
        self.context = None
