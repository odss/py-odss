import pytest


@pytest.fixture()
@pytest.mark.asyncio
async def cdi(framework):
    bundle = await framework.install_bundle("odss.cdi.core")
    await bundle.start()

    yield framework
    await bundle.stop()
    await framework.uninstall_bundle(bundle)


@pytest.fixture()
@pytest.mark.asyncio
async def components(cdi):
    bundle = await cdi.install_bundle("tests.cdi.components")

    await bundle.start()

    yield cdi

    await bundle.stop()
    await cdi.uninstall_bundle(bundle)
