import binascii
import base64
from .abc import IStorage
from .consts import DEFAULT_COOKIE_PARAMS, CookieParams
from odss.http.common import Request


class CookieStorage(IStorage):
    def __init__(
        self,
        cookie_name: str = "ct",
        cookie_params: CookieParams | None = None,
    ):
        self.cookie_name = cookie_name
        self.cookie_params = DEFAULT_COOKIE_PARAMS.copy()
        self.cookie_params.update(cookie_params or {})

    async def get_secret(self, request: Request) -> bytes | None:
        try:
            secret = request.cookies[self.cookie_name]
            return base64.b64decode(secret)
        except (KeyError, binascii.Error):
            return None

    async def save_secret(self, response, secret: bytes) -> None:
        value = base64.b64encode(secret).decode()
        response.cookies.set(self.cookie_name, value, **self.cookie_params)
