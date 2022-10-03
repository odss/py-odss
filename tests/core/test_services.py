import pytest

from odss.core.bundle import BundleContext
from odss.core.errors import BundleException
from tests.core.interfaces import ITextService
from tests.utils import TEXT_BUNDLE, TRANSLATE_BUNDLE


@pytest.mark.asyncio
async def test_install(framework):
    context = framework.get_context()
    assert isinstance(context, BundleContext)
    bundle = await context.install_bundle(TEXT_BUNDLE)
    assert bundle.get_context() is None

    ref = context.get_service_reference()
    assert ref is None

    ref = context.get_service_references()
    assert ref == []

    ref1 = context.get_service_reference(ITextService)
    assert ref1 is None

    refs = context.get_service_references(ITextService)
    assert refs == []

    await bundle.start()

    ref = context.get_service_reference()
    assert ref is not None

    refs = context.get_service_references()
    assert len(refs) == 2

    ref1 = context.get_service_reference(ITextService)
    assert ref1 is not None

    query = {"name": "drunk"}
    ref2 = context.get_service_reference(ITextService, query)
    assert ref2 is not None
    assert ref2.get_property("name") == "drunk"

    query = {"name": "normal"}
    ref2 = context.get_service_reference(ITextService, query)
    assert ref2 is not None
    assert ref2.get_property("name") == "normal"

    refs = context.get_service_references(ITextService)
    assert len(refs) == 2

    query = {"type": "text"}
    refs = context.get_service_references(None, query)
    assert len(refs) == 2

    query = "(type=text)"
    refs = context.get_service_references(None, query)
    assert len(refs) == 2

    query = {"name": "normal"}
    refs2 = context.get_service_references(ITextService, query)
    assert len(refs2) == 1

    query = {"name": "drunk"}
    ref = context.get_service_reference(ITextService, query)
    service = context.get_service(ref)
    assert service.echo("foobar") == "raboof"

    context.unget_service(ref)

    await bundle.stop()

    ref1 = context.get_service_reference(ITextService)
    assert ref1 is None

    refs1 = context.get_service_references(ITextService)
    assert refs1 == []

    refs = bundle.get_references()
    assert len(refs) == 0


@pytest.mark.asyncio
async def test_service_bundle_using(framework):
    context = framework.get_context()
    bundle_text = await context.install_bundle(TEXT_BUNDLE)
    bundle_translate = await context.install_bundle(TRANSLATE_BUNDLE)

    refs = bundle_text.get_references()
    assert len(refs) == 0

    refs = bundle_text.get_using_services()
    assert len(refs) == 0

    refs = bundle_translate.get_using_services()
    assert len(refs) == 0

    refs = bundle_translate.get_references()
    assert len(refs) == 0

    await bundle_text.start()
    await bundle_translate.start()

    refs = bundle_text.get_references()
    assert len(refs) == 2

    refs = bundle_translate.get_references()
    assert len(refs) == 1

    refs = bundle_text.get_using_services()
    assert len(refs) == 0

    refs = bundle_translate.get_using_services()
    assert len(refs) == 0

    ctx = bundle_translate.get_context()
    ref = ctx.get_service_reference(ITextService)
    service = ctx.get_service(ref)

    refs = bundle_text.get_using_services()
    assert len(refs) == 0

    refs = bundle_translate.get_using_services()
    assert len(refs) == 1

    ctx.unget_service(ref)

    refs = bundle_text.get_using_services()
    assert len(refs) == 0

    refs = bundle_translate.get_using_services()
    assert len(refs) == 0


@pytest.mark.asyncio
async def test_unregister_service(framework):
    context = framework.get_context()
    registration = await  context.register_service("foo", "bar")

    reference = context.get_service_reference("foo")
    assert reference is not None
    service = context.get_service(reference)
    assert service == "bar"

    await registration.unregister()

    # unregister twice
    with pytest.raises(BundleException):
        await registration.unregister()

    with pytest.raises(BundleException):
        context.get_service(reference)
