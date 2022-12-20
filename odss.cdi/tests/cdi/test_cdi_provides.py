import asyncio

import pytest
from odss.common import BundleEvent, ServiceEvent

from tests.cdi.interfaces import IListener, IManager, IService, IStorage


@pytest.mark.usefixtures("cdi")
async def test_priovides_services(framework):
    class BundleListener:
        def __init__(self, event, counter):
            self.event = event
            self.counter = counter

        def bundle_changed(self, event):
            if event.kind == BundleEvent.STARTED:
                self.counter -= 1
                if self.counter == 0:
                    self.event.set()

    class ServiceListener:
        def __init__(self, event, counter):
            self.event = event
            self.counter = counter

        def service_changed(self, event):
            if event.kind == ServiceEvent.REGISTERED:
                self.counter -= 1
            if self.counter == 0:
                self.event.set()

    ctx = framework.get_context()
    bevent = asyncio.Event()
    sevent = asyncio.Event()
    ctx.add_bundle_listener(BundleListener(bevent, 1))
    ctx.add_service_listener(ServiceListener(sevent, 1))

    bundle = await framework.install_bundle("tests.cdi.components")

    refs = framework.find_service_references(IService)
    assert len(refs) == 0

    refs = framework.find_service_references(IStorage)
    assert len(refs) == 0

    refs = framework.find_service_references(IListener)
    assert len(refs) == 0

    refs = framework.find_service_references(IManager)
    assert len(refs) == 0

    await bundle.start()

    await bevent.wait()
    await sevent.wait()

    refs = framework.find_service_references(IService)
    assert len(refs) == 1

    refs = framework.find_service_references(IStorage)
    assert len(refs) == 1

    refs = framework.find_service_references(IListener)
    assert len(refs) == 1

    refs = framework.find_service_references(IManager)
    assert len(refs) == 1

    await bundle.stop()

    refs = framework.find_service_references(IService)
    assert len(refs) == 0

    refs = framework.find_service_references(IStorage)
    assert len(refs) == 0

    refs = framework.find_service_references(IListener)
    assert len(refs) == 0

    refs = framework.find_service_references(IManager)
    assert len(refs) == 0

    await framework.uninstall_bundle(bundle)
