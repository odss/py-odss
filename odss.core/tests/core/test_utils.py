import pytest

from odss.core.utils import class_name, classes_name
from tests.core.interfaces import ITextService

IECHO_NAME = "tests.core.interfaces.ITextService"


def test_class_name():
    assert class_name("foo.bar") == "foo.bar"
    assert class_name(ITextService) == IECHO_NAME

    with pytest.raises(ValueError):
        assert class_name({})


def test_classes_name():
    assert classes_name(["foo.bar", ITextService]) == ("foo.bar", IECHO_NAME)
