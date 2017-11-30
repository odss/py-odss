import pytest

from odss import create_framework
from odss.bundle import Bundle
from odss.errors import BundleException

from tests.utils import FrameworkListener


ECHO_BUNDLE = 'tests.bundles.echo'


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

    bundle = framework.install_bundle(ECHO_BUNDLE)

    await framework.start()
    
    await framework.stop()
