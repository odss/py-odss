import pytest

from odss.core.trackers import ServiceTracker
from tests.utils import TEXT_BUNDLE, TRANSLATE_BUNDLE
from tests.core.interfaces import ITextService


@pytest.mark.asyncio
async def test_simple_tracker(framework):
    context = framework.get_context()

    bundle = await context.install_bundle(TEXT_BUNDLE)
    await bundle.start()

    tracker = TextServiceTracker(context)
    await tracker.open()

    assert len(tracker.get_service_references()) == 2
    assert tracker.get_service_reference() is not None
    assert len(tracker.get_services()) == 2
    assert tracker.get_service() is not None
    await tracker.close()

    tracker = TextServiceTracker(context, {"name": "drunk"})
    await tracker.open()

    assert len(tracker.get_service_references()) == 1
    assert tracker.get_service().echo("Foo") == "ooF"

    await bundle.stop()

    assert len(tracker.get_service_references()) == 0

    await tracker.close()


@pytest.mark.asyncio
async def test_listener_tracker(framework):
    context = framework.get_context()

    tracker = TextServiceTracker(context)
    await tracker.open()

    bundle = await context.install_bundle(TEXT_BUNDLE)
    await bundle.start()

    assert len(tracker.get_service_references()) == 2

    assert len(tracker.events) == 2
    assert tracker.events[0][0] == "on_adding_service"
    assert tracker.events[1][0] == "on_adding_service"

    await bundle.stop()

    assert len(tracker.events) == 4
    assert tracker.events[2][0] == "on_removed_service"
    assert tracker.events[3][0] == "on_removed_service"


class TextServiceTracker(ServiceTracker):
    def __init__(self, ctx, query=None):
        super().__init__(self, ctx, ITextService, query)
        self.events = []

    async def on_adding_service(self, reference, service):
        self.events.append(("on_adding_service", reference, service))

    async def on_modified_service(self, reference, service):
        self.events.append(("on_modified_service", reference, service))

    async def on_removed_service(self, reference, service):
        self.events.append(("on_removed_service", reference, service))
