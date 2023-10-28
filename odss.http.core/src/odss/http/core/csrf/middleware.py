import binascii
import base64
import typing as t
from secrets import compare_digest, token_bytes

from odss.http.common import ODSS_HTTP_REQUEST_CSRF, HttpForbidden, HttpError

from .crypto import mask_token, unmask_token
from .abc import IStorage, IPolicy

from .consts import PROTECTED_METHODS, SECRET_LENGTH

CSFR_SECRET = "csrf.secret"
CSFR_SECRET_UPDATE = "csfr.secret.update"


class RejectRequest(Exception):
    def __init__(self, reason: str):
        self.reason = reason


class CsrfMiddleware:
    def __init__(self, storage: IStorage, policy: IPolicy):
        self.storage = storage
        self.policy = policy

    async def __call__(self, request, handler):
        secret = await self.storage.get_secret(request)
        if request.method in PROTECTED_METHODS:
            if secret is None:
                raise HttpForbidden("CSRF cookie not set.")
            token = await self.policy.get_token(request)
            if token is None:
                raise HttpForbidden("CSRF token missing.")

            if not compare_digest(unmask_token(token), secret):
                raise HttpForbidden("CSRF token incorrect.")

        request[ODSS_HTTP_REQUEST_CSRF] = Crsf(request, secret)
        try:
            response = await handler(request)
        except HttpError as ex:
            await self.check_response(request, ex)
            raise ex
        await self.check_response(request, response)
        request.csrf = None
        return response

    async def check_response(self, request, response):
        try:
            secret = request[CSFR_SECRET_UPDATE]
            del request[CSFR_SECRET_UPDATE]
            await self.storage.save_secret(response, secret)
        except KeyError:
            pass


class Crsf:
    def __init__(self, request, secret):
        self._request = request
        self._secret = secret

    def token(self) -> str:
        if self._secret is None:
            self.regenerate()
        token = mask_token(t.cast(bytes, self._secret))
        return base64.b64encode(token).decode()

    def verify(self, token: str) -> bool:
        if self._secret and token:
            try:
                decoded_token = base64.b64decode(token)
                return len(decoded_token) > 0 and compare_digest(
                    unmask_token(decoded_token), self._secret
                )
            except binascii.Error:
                pass
        return False

    def regenerate(self) -> None:
        self._secret = token_bytes(SECRET_LENGTH)
        self._request[CSFR_SECRET_UPDATE] = self._secret
