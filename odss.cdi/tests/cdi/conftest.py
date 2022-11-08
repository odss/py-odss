import pytest_asyncio


@pytest_asyncio.fixture
async def cdi(framework):
    bundle = await framework.install_bundle("odss.cdi.bundle")
    await bundle.start()

    yield framework
    await bundle.stop()
    await framework.uninstall_bundle(bundle)


@pytest_asyncio.fixture
async def components(cdi):
    bundle = await cdi.install_bundle("tests.cdi.components")

    await bundle.start()

    yield cdi

    await bundle.stop()
    await cdi.uninstall_bundle(bundle)
