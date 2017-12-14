import pytest

from odss.core import create_framework
from odss.core.bundle import Bundle
from odss.core.errors import BundleException
from tests.utils import SIMPLE_BUNDLE


@pytest.mark.asyncio
async def test_initial_framework():
    framework = await create_framework()
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

    bundle = await framework.install_bundle(SIMPLE_BUNDLE)

    assert bundle == framework.get_bundle_by_id(bundle.id)
    assert bundle == framework.get_bundle_by_name(bundle.name)

    await framework.uninstall_bundle(bundle)
    with pytest.raises(BundleException):
        assert bundle == framework.get_bundle_by_id(bundle.id)
    with pytest.raises(BundleException):
        assert bundle == framework.get_bundle_by_name(bundle.name)


@pytest.mark.asyncio
async def test_install_bundle_in_resolved_framework(framework):
    bundle = await framework.install_bundle(SIMPLE_BUNDLE)
    assert bundle.state == Bundle.RESOLVED
    await framework.uninstall_bundle(bundle)

    with pytest.raises(BundleException):
        framework.get_bundle_by_id(bundle.id)

    await framework.start()

    bundle = await framework.install_bundle(SIMPLE_BUNDLE)
    assert bundle.state == Bundle.RESOLVED
    await bundle.start()
    assert bundle.state == Bundle.ACTIVE

    await framework.stop()


@pytest.mark.asyncio
async def test_install_bundle_with_errors(framework):
    bundle = await framework.install_bundle(SIMPLE_BUNDLE)

    await bundle.start()
    assert bundle.state == Bundle.RESOLVED

    await framework.start()
    assert bundle.state == Bundle.ACTIVE

    await bundle.start()
    assert bundle.state == Bundle.ACTIVE
    await bundle.stop()
    assert bundle.state == Bundle.RESOLVED

    bundle.get_module().throw_error = True
    with pytest.raises(BundleException):
        await bundle.start()
    assert bundle.state == Bundle.RESOLVED

    await bundle.start()
    assert bundle.state == Bundle.ACTIVE

    bundle.get_module().throw_error = True
    with pytest.raises(BundleException):
        await bundle.stop()
    assert bundle.state == Bundle.ACTIVE

    await framework.stop()
    assert bundle.state == Bundle.RESOLVED
