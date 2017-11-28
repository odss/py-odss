from .framework import Framework

def create_framework(bundles, settings):
    framework = Framework(settings)
    for bundle_name in bundles:
        framework.install_bundle(bundle_name)
    return framework

