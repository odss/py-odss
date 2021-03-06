from odss.core import Callback

TEXT_BUNDLE = "tests.bundles.text"
SIMPLE_BUNDLE = "tests.bundles.simple"
TRANSLATE_BUNDLE = "tests.bundles.translate"
NO_BUNDLE = "tests.bundles.empty"


class Listener:
    def __init__(self):
        self.events = []
        self.names = []

    def __len__(self):
        return len(self.events)

    def last_event(self):
        return self.events[-1]


class ServiceListener(Listener):
    async def service_changed(self, event):
        self.events.append(event)
        self.names.append("service_changed")


class FrameworkListener(Listener):
    async def framework_changed(self, event):
        self.events.append(event)
        self.names.append("framework_changed")


class BundleListener(Listener):
    async def bundle_changed(self, event):
        self.events.append(event)
        self.names.append("bundle_changed")


class AllListener(FrameworkListener, BundleListener, ServiceListener):
    pass
