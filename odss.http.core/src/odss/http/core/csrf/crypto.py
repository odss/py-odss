import itertools
import secrets

from .consts import SECRET_LENGTH


def one_time_pad(msg: bytes, key: bytes) -> bytes:
    """
    @see https://en.wikipedia.org/wiki/One-time_pad
    """
    return bytes(x ^ y for x, y in zip(msg, itertools.cycle(key)))


def mask_token(token: bytes) -> bytes:
    key = secrets.token_bytes(SECRET_LENGTH)
    return key + one_time_pad(token, key)


def unmask_token(data: bytes) -> bytes:
    key, token = data[:SECRET_LENGTH], data[SECRET_LENGTH:]
    return one_time_pad(token, key)
