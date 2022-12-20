import pytest

from odss.http.common import encode_json, decode_json, JSONError


def test_encode_json():
    data = encode_json(["test", 1, False, None])
    assert data == '["test",1,false,null]'


def test_decode_json():
    data = decode_json('["test",1,false,null]')
    assert data == ["test", 1, False, None]


def test_encode_json_error():
    d = {}
    d["d"] = d

    with pytest.raises(JSONError):
        encode_json(d)

    del d["d"]


def test_decode_json_error():
    with pytest.raises(JSONError):
        decode_json("[")
