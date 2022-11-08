from odss.cdi.decorators import bind, component, invalidate, provides, unbind, validate

from .interfaces import IListener, IManager, IService, IStorage

EVENTS = []


@component
@provides(IService)
class MyService:
    def __init__(self) -> None:
        print("MyService")

    pass


@component
@provides(IStorage)
class MyStorage:
    pass


@component
@provides(IListener)
class MyListener:
    pass


@component
@provides(IManager)
class ManagerComponent:
    def __init__(self, service: IService, storage: IStorage):
        self.service = service
        self.storage = storage

    @bind
    def add_listener(self, listener: IListener):
        EVENTS.append(("add_listener", listener))

    @unbind
    def remove_listener(self, listener: IListener):
        EVENTS.append(("remove_listener", listener))

    @validate
    def validate(self, ctx):
        EVENTS.append(("validate", ctx))

    @invalidate
    def invalidate(self, ctx):
        EVENTS.append(("invalidate", ctx))
