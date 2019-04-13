from odss.cdi.decorators import Component, Provides, Bind, Unbind, Validate, Invalidate
from .interfaces import IService, IStorage, IListener, IManager


@Component
@Provides(IService)
class MyService:
    pass


@Component
@Provides(IStorage)
class MyStorage:
    pass


@Component
@Provides(IListener)
class MyListener:
    pass


EVENTS = []


@Component
@Provides(IManager)
class ManagerComponent:
    def __init__(self, service: IService, storage: IStorage):
        self.service = service
        self.storage = storage

    @Bind
    def add_listener(self, listener: IListener):
        EVENTS.append(("add_listener", listener))

    @Unbind
    def remove_listener(self, listener: IListener):
        EVENTS.append(("remove_listener", listener))

    @Validate
    def validate(self, ctx):
        EVENTS.append(("validate", ctx))

    @Invalidate
    def invalidate(self, ctx):
        EVENTS.append(("invalidate", ctx))
