import pytest

from odss.http.common import JsonError, decode_json, encode_json


def test_encode_json():
    data = encode_json(["test", 1, False, None])
    assert data == '["test",1,false,null]'


def test_decode_json():
    data = decode_json('["test",1,false,null]')
    assert data == ["test", 1, False, None]


def test_encode_json_error():
    d = {}
    d["d"] = d

    with pytest.raises(JsonError):
        encode_json(d)

    del d["d"]


def test_decode_json_error():
    with pytest.raises(JsonError):
        decode_json("[")
