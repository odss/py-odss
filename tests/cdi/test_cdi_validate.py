import pytest

from tests.cdi.interfaces import IService, IStorage, IListener, IManager


@pytest.mark.asyncio
@pytest.mark.usefixtures("cdi")
async def test_priovides_services(framework):
    bundle = await framework.install_bundle("tests.cdi.components")
    module = bundle.get_module()

    assert len(module.EVENTS) == 0

    await bundle.start()

    assert len(module.EVENTS) == 2
    assert module.EVENTS[0][0] == "validate"

    await bundle.stop()

    assert len(module.EVENTS) == 4
    assert module.EVENTS[3][0] == "invalidate"

    del module.EVENTS[:]
    await framework.uninstall_bundle(bundle)
