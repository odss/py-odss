import pytest
from odss.common.utils import get_class_name, get_classes_name


IECHO_NAME = "test_utils.ITextService"


class ITextService:
    pass


def test_class_name():
    assert get_class_name("foo.bar") == "foo.bar"
    assert get_class_name(ITextService) == IECHO_NAME

    with pytest.raises(ValueError):
        assert get_class_name({})


def test_classes_name():
    assert get_classes_name(["foo.bar", ITextService]) == ("foo.bar", IECHO_NAME)
