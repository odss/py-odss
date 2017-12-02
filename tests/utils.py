
ECHO_BUNDLE = 'tests.bundles.echo'
SIMPLE_BUNLE = 'tests.bundles.simple'


class Listener:
    def __init__(self):
        self.events = []
        self.names = []

    def __len__(self):
        return len(self.events)

    def last_event(self):
        return self.events[-1]


class ServiceListener(Listener):
    def service_changed(self, event):
        self.events.append(event)
        self.names.append('service_changed')


class FrameworkListener(Listener):
    def framework_changed(self, event):
        self.events.append(event)
        self.names.append('framework_changed')


class BundleListener(Listener):
    def bundle_changed(self, event):
        self.events.append(event)
        self.names.append('bundle_changed')


class AllListener(FrameworkListener, BundleListener, ServiceListener):
    pass
