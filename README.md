# odss
## Open Dynamic Services

Becuse I like OSGi (The Dynamic Module System for Java)[https://www.osgi.org/] idea, and python IPOPO [https://github.com/tcalmant/ipopo], I try to implement the async way.


### Framework
> api.py
```python
class IService:
    pass


class IListener:
    pass


class IStorage:
    pass


class IManager:
    pass
```
> bundle.py
```python
from odss.framework.bundle import IBundleContext

from .api import IService, IStorage, IListener, IManager

class Activator:
    async start(self, ctx: IBundleContext) -> None:
        ref = ctx.get_reference(IStorage)
        storage = ctx.get_service(ref)
        manager = StorageManager(storage)
        self.registration = await ctx.register_service(IManager, manager)

    async stop(self, ctx: IBundleContext) -> None:
        await self.registration.unregister()
```

> main.py
```python
from odss.framework import create_framework

# ...
framework = await create_framework()
await framework.start()
bundle = await framework.install_bundle('bundle')
await bundle.start()

# ...
await bundle.stop()

await framework.uninstall_bundle()
```

## CDI - Component Dependency injection
More easy way to setup dependency (iPOPO like)
```python
from odss import cdi
from .interfaces import IService, IStorage, IListener, IManager


@cdi.component
@cdi.provides(IService)
class MyService:
    pass


@cdi.component
@cdi.provides(IStorage)
class MyStorage:
    pass


@cdi.component
@cdi.provides(IListener)
class MyListener:
    pass


@cdi.component
@cdi.provides(IManager)
class ManagerComponent:
    def __init__(self, service: IService, storage: IStorage):
        self.service = service
        self.storage = storage

    @cdi.bind
    def add_listener(self, listener: IListener):
        # ...

    @cdi.unbind
    def remove_listener(self, listener: IListener):
        # ...

    @cdi.validate
    def validate(self, ctx):
        # ...

    @cdi.invalidate
    def invalidate(self, ctx):
        # ...
```

## License
MIT
