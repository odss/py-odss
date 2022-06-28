import asyncio
import pytest

from tests.cdi.interfaces import IListener, IManager, IService, IStorage


@pytest.mark.asyncio
@pytest.mark.usefixtures("cdi")
async def test_provides_services(framework):
    bundle = await framework.install_bundle("tests.cdi.components")
    module = bundle.get_module()

    await bundle.start()

    assert len(module.EVENTS) == 2
    assert module.EVENTS[0][0] == "validate"

    await bundle.stop()

    assert len(module.EVENTS) == 4
    assert module.EVENTS[3][0] == "invalidate"

    await framework.uninstall_bundle(bundle)
