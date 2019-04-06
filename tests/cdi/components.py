from odss.cdi.decorators import Component, Provides, Bind, Unbind, Validate, Invalidate
from .interfaces import IService, IStorage, IListener


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


@Component
class ManagerComponent:
    def __init__(self, service: IService, storage: IStorage):
        self.service = service
        self.storage = storage

    @Bind
    def add_listener(self, listener: IListener):
        pass

    @Unbind
    def remove_listener(self, listener: IListener):
        pass

    @Validate
    def validate(self, ctx):
        pass

    @Invalidate
    def invalidate(self, ctx):
        pass
