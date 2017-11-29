from tests.interfaces import IEchoServcie


class DrunkEchoServcie:
    def echo(self, message):
        return message[::-1]  


class Activator:
    def start(self, context):
        service = DrunkEchoServcie()
        properties = {'name': 'drunk'}
        self.registration = context.register(IEchoServcie, service, properties)
    
    def stop(self, context):
        self.registration.unregister()
