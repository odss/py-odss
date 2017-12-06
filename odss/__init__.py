from .framework import Framework


async def create_framework(settings=None, bundles=None):
    framework = Framework(settings)
    if bundles:
        for symbolic_name in bundles:
            await framework.install_bundle(symbolic_name)
    return framework
