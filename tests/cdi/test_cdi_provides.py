import pytest

from tests.cdi.interfaces import IListener, IManager, IService, IStorage


@pytest.mark.asyncio
@pytest.mark.usefixtures("cdi")
async def test_priovides_services(framework):
    bundle = await framework.install_bundle("tests.cdi.components")
    await bundle.start()

    refs = framework.find_service_references(IManager)
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
