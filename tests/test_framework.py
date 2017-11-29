
import pytest

from odss import create_framework
from odss.bundle import Bundle
from odss.errors import BundleException


SIMPLE_BUNDLE = 'tests.bundles.simple'
ECHO_BUNDLE = 'tests.bundles.echo'


class FrameworkListener:
    async def framework_changed(self, event):
        self.event = event


@pytest.fixture()
def listener():
    return FrameworkListener()

def test_initial_framework():
    framework = create_framework()
    bundle = framework.get_bundle_by_id(0)
    assert bundle == framework
    bundle = framework.get_bundle_by_name(framework.name)
    assert bundle == framework
    
    with pytest.raises(BundleException):
        assert framework.get_bundle_by_name('test') == None
    with pytest.raises(BundleException):
        assert framework.get_bundle_by_id(1) == None


@pytest.mark.asyncio
async def test_start_with_bundle(listener):
    framework = create_framework()
    
    context = framework.get_context()
    context.add_framework_listener(listener)

    
    await framework.start()
    
    await framework.stop()
