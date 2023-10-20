from .framework import Framework

__version__ = (0, 0, 1)


async def create_framework(properties=None, bundles=None):
    #    properties = {} if properties is None else properties
    framework = Framework(properties)
    if bundles:
        for symbolic_name in bundles:
            await framework.install_bundle(symbolic_name)
    return framework
