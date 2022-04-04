from odss.core.bundle import BundleContext
from tests.core.interfaces import ITranslateService

TRANSLATE = {"hello": "cześć", "world": "świat"}


class TranslateService:
    def translate(self, term):
        return TRANSLATE.get(term, term)


class Activator:
    def start(self, context):
        assert isinstance(context, BundleContext)
        props = {"locale": "pl"}
        Activator.service_registration = context.register_service(
            ITranslateService, TranslateService(), props
        )

    def stop(self, context):
        assert isinstance(context, BundleContext)
        Activator.service_registration.unregister()
