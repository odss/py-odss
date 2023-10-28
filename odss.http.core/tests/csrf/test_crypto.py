from odss.http.core.csrf.crypto import one_time_pad, mask_token, unmask_token


def test_one_time_pad():
    data = b"Lorem ipsum dolor sit amu."
    key = b"Vivamus scelerisque arcur."
    expected = b"\x1a\x06\x04\x04\x00U\x1aP\x00\x16\x08L\x01\x1d\x05\x1c\x03U\x16I\x15R\x02\x18\x07\x00"

    assert one_time_pad(data, key) == expected


def test_umask_token():
    token = b"12345678901234567890123456789012"
    full_token = mask_token(token)
    result = unmask_token(full_token)

    assert token == result
