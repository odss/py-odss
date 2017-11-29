from odss.bundle import BundleContext


class Activator:
    def start(self, context):
        assert isinstance(context, BundleContext)
        self.context = context

    def stop(self, context):
        assert isinstance(context, BundleContext)
        self.context = None