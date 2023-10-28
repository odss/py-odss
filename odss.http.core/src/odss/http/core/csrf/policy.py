import binascii
import base64
import typing as t

from odss.http.common import Request

from .abc import IPolicy


class HeaderPolicy(IPolicy):
    def __init__(self, header_name: str = "X-CT") -> None:
        self.header_name = header_name

    async def get_token(self, request: Request) -> bytes | None:
        try:
            token = request.headers[self.header_name]
            return base64.b64decode(token)
        except (KeyError, binascii.Error):
            return None


class FormPolicy(IPolicy):
    def __init__(self, field_name: str = "ct") -> None:
        self.field_name = field_name

    async def get_token(self, request: Request) -> bytes | None:
        post = await request.post()
        try:
            token = post[self.field_name]
            return base64.b64decode(t.cast(str, token))
        except (KeyError, binascii.Error):
            return None


class FormAndHeaderPolicy(IPolicy):
    def __init__(self, field_name: str = "ct", header_name: str = "X-CT") -> None:
        self.policies = [FormPolicy(field_name), HeaderPolicy(header_name)]

    async def get_token(self, request: Request) -> bytes | None:
        for policy in self.policies:
            token = await policy.get_token(request)
            if token is not None:
                return token
        return None
