import pytest

from tests.cdi.interfaces import IService, IStorage, IListener


@pytest.mark.asyncio
async def test_priovides_services(framework):
    bundle = await framework.install_bundle("odss.cdi.core")
    await bundle.start()

    bundle = await framework.install_bundle("tests.cdi.components")
    await bundle.start()

    refs = framework.find_service_references(IService)
    assert len(refs) == 1

    refs = framework.find_service_references(IStorage)
    assert len(refs) == 1

    refs = framework.find_service_references(IListener)
    assert len(refs) == 1

    await bundle.stop()

    refs = framework.find_service_references(IService)
    assert len(refs) == 0

    refs = framework.find_service_references(IStorage)
    assert len(refs) == 0

    refs = framework.find_service_references(IListener)
    assert len(refs) == 0
