import pytest

from odss.errors import BundleException
from odss.utils import class_name, classes_name
from tests.interfaces import ITextService

IECHO_NAME = 'tests.interfaces.ITextService'


def test_class_name():
    assert class_name('foo.bar') == 'foo.bar'
    assert class_name(ITextService) == IECHO_NAME

    with pytest.raises(BundleException):
        assert class_name({})


def test_classes_name():
    assert classes_name(['foo.bar', ITextService]) == ('foo.bar', IECHO_NAME)
