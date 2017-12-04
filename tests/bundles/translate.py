from odss.bundle import BundleContext
from tests.interfaces import ITranslateService


TRANSLATE = {
    'hello': 'cześć',
    'world': 'świat'
}


class TranslateService:
    def translate(self, term):
        return TRANSLATE.get(term, term)


class Activator:
    def start(self, context):
        assert isinstance(context, BundleContext)
        props = {'locale': 'pl'}
        self.reg = context.register_service(
            ITranslateService, TranslateService(), props)

    def stop(self, context):
        assert isinstance(context, BundleContext)
        self.reg.unregister()
