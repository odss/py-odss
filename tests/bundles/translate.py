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
    async def start(self, context):
        assert isinstance(context, BundleContext)
        props = {'locale': 'pl'}
        self.reg = await context.register_service(
            ITranslateService, TranslateService(), props)

    async def stop(self, context):
        assert isinstance(context, BundleContext)
        await self.reg.unregister()
