from odss.core.bundle import BundleContext

throw_error = False


class Activator:
    def __init__(self):
        self._raise = False

    def start(self, context):
        assert isinstance(context, BundleContext)
        self.context = context

        global throw_error
        if throw_error:
            throw_error = False
            raise Exception(":(")

    def stop(self, context):
        assert isinstance(context, BundleContext)

        global throw_error
        if throw_error:
            throw_error = False
            raise Exception(":(")
