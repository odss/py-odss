import pytest

from odss.core.bundle import BundleContext
from odss.core.errors import BundleException
from tests.interfaces import ITextService
from tests.utils import TEXT_BUNDLE


@pytest.mark.asyncio
@pytest.mark.usefixtures("active")
async def test_install(framework):
    context = framework.get_context()
    assert isinstance(context, BundleContext)
    bundle = await context.install_bundle(TEXT_BUNDLE)
    assert bundle.get_context() is None

    with pytest.raises(BundleException):
        ref1 = context.get_service_reference(None)

    ref1 = context.get_service_reference(ITextService)
    assert ref1 is None

    refs = context.get_service_references(ITextService)
    assert refs == []

    await bundle.start()

    ref1 = context.get_service_reference(ITextService)
    assert ref1 is not None

    query = {'name': 'drunk'}
    ref2 = context.get_service_reference(ITextService, query)
    assert ref2 is not None
    assert ref2.get_property('name') == 'drunk'

    query = {'name': 'normal'}
    ref2 = context.get_service_reference(ITextService, query)
    assert ref2 is not None
    assert ref2.get_property('name') == 'normal'

    refs1 = context.get_service_references(ITextService)
    assert len(refs1) == 2

    query = {'name': 'normal'}
    refs2 = context.get_service_references(ITextService, query)
    assert len(refs2) == 1

    query = {'name': 'drunk'}
    ref = context.get_service_reference(ITextService, query)
    service = context.get_service(ref)
    assert service.echo('foobar') == 'raboof'

    context.unget_service(ref)

    await bundle.stop()

    ref1 = context.get_service_reference(ITextService)
    assert ref1 is None

    refs1 = context.get_service_references(ITextService)
    assert refs1 == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("active")
async def test_unregister_service(framework):
    context = framework.get_context()
    registration = await context.register_service('foo', 'bar')

    reference = context.get_service_reference('foo')
    assert reference is not None
    service = context.get_service(reference)
    assert service == 'bar'

    await registration.unregister()

    # unregister twice
    with pytest.raises(BundleException):
        await registration.unregister()

    with pytest.raises(BundleException):
        context.get_service(reference)
