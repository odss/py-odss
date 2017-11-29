
import pytest

from odss import create_framework
from odss.bundle import Bundle
from odss.errors import BundleException


SIMPLE_BUNDLE = 'tests.bundles.simple'
ECHO_BUNDLE = 'tests.bundles.echo'


def test_initial_framework():
    framework = create_framework()
    bundle = framework.get_bundle_by_id(0)
    assert bundle == framework
    bundle = framework.get_bundle_by_name(framework.name)
    assert bundle == framework
    
    with pytest.raises(BundleException):
        assert framework.get_bundle_by_name('test') == None
    with pytest.raises(BundleException):
        assert framework.get_bundle_by_id(1) == None


def test_start_with_bundle():
    framework = create_framework()
    bundle = framework.install_bundle(SIMPLE_BUNDLE)

    assert bundle.state == Bundle.RESOLVED, 'Bundle should be in RESOLVED state'

    framework.start()

    assert bundle.state == Bundle.ACTIVE, 'Bundle should be in ACTIVE state'

    framework.stop()

    assert bundle.state == Bundle.RESOLVED, 'Bundle should be in RESOLVED state'

