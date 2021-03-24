from odss.core.bundle import BundleContext
from tests.core.interfaces import ITranslateService

TRANSLATE = {"hello": "cześć", "world": "świat"}


class TranslateService:
    def translate(self, term):
        return TRANSLATE.get(term, term)


class Activator:
    async def start(self, context):
        assert isinstance(context, BundleContext)
        props = {"locale": "pl"}
        Activator.service_registration = await context.register_service(
            ITranslateService, TranslateService(), props
        )

    async def stop(self, context):
        assert isinstance(context, BundleContext)
        await Activator.service_registration.unregister()
