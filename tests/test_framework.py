import pytest

from odss import create_framework
from odss.bundle import Bundle
from odss.errors import BundleException

from tests.utils import FrameworkListener


ECHO_BUNDLE = 'tests.bundles.echo'
SIMPLE_BUNLE = 'tests.bundles.simple'


@pytest.fixture()
def listener():
    return FrameworkListener()


@pytest.fixture()
def framework():
    return create_framework()


@pytest.fixture
@pytest.mark.asyncio
async def active(framework):
    await framework.start()
    yield
    await framework.stop()
    
def test_initial_framework():
    framework = create_framework()
    bundle = framework.get_bundle_by_id(0)
    assert bundle == framework
    bundle = framework.get_bundle_by_name(framework.name)
    assert bundle == framework
    
    with pytest.raises(BundleException):
        framework.get_bundle_by_name('test')

    with pytest.raises(BundleException):
        framework.get_bundle_by_id(1)


@pytest.mark.asyncio
async def test_start_and_stop(framework):    
    assert framework.state == Bundle.RESOLVED
    
    await framework.start()
    
    assert framework.state == Bundle.ACTIVE
    
    await framework.stop()

    assert framework.state == Bundle.RESOLVED

@pytest.mark.asyncio
@pytest.mark.usefixtures("active")
async def test_install_uninstall_bundle(framework):

    bundle = await framework.install_bundle(SIMPLE_BUNLE)
    
    assert bundle == framework.get_bundle_by_id(bundle.id)
    assert bundle == framework.get_bundle_by_name(bundle.name)

    
    await framework.uninstall_bundle(bundle)
    with pytest.raises(BundleException):
        assert bundle == framework.get_bundle_by_id(bundle.id)
    with pytest.raises(BundleException):
        assert bundle == framework.get_bundle_by_name(bundle.name)


@pytest.mark.asyncio
async def test_install_bundle_in_resolved_framework(framework):
    bundle = await framework.install_bundle(SIMPLE_BUNLE)
    assert bundle.state == Bundle.RESOLVED
    await framework.uninstall_bundle(bundle)

    await framework.start()

    bundle = await framework.install_bundle(SIMPLE_BUNLE)
    assert bundle.state == Bundle.ACTIVE
    
@pytest.mark.asyncio
async def test_install_bundle_with_errors(framework):
    bundle = await framework.install_bundle(SIMPLE_BUNLE)
    
    await bundle.start()
    assert bundle.state == Bundle.RESOLVED

    await bundle.stop()
    assert bundle.state == Bundle.RESOLVED
    
    bundle.module.throw_error = True
    with pytest.raises(BundleException):
        await bundle.start()
    assert bundle.state == Bundle.RESOLVED

    await bundle.start()
    bundle.module.throw_error = True
    with pytest.raises(BundleException):
        await bundle.stop()
    assert bundle.state == Bundle.ACTIVE

    import ipdb; ipdb.set_trace()
    await framework.stop()

    assert bundle.state == Bundle.RESOLVED

