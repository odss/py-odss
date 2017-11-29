from .framework import Framework


def create_framework(settings=None, bundles=None):
    framework = Framework(settings)
    if bundles:
        for symbolic_name in bundles:
            framework.install_bundle(symbolic_name)
    return framework

