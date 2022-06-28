from .framework import Framework
from .loop import Callback  # noqa.
from .consts import SERVICE_ID, OBJECTCLASS, SERVICE_BUNDLE_ID, SERVICE_PRIORITY
from .types import IBundle, IBundleContext


async def create_framework(settings=None, bundles=None):
    framework = Framework(settings)
    if bundles:
        for symbolic_name in bundles:
            await framework.install_bundle(symbolic_name)
    return framework
