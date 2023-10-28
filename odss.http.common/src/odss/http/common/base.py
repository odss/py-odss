import typing as t
from http.cookies import SimpleCookie

from multidict import CIMultiDict

from .consts import ODSS_HTTP_REQUEST_CSRF
from .abc import ICsrf, Request

try:
    import ujson as json
except ImportError:
    import json  # type: ignore[no-redef]

from .abc import AuthInfo, Request, IHttpSecurityPolicy


class JsonError(Exception):
    pass


def decode_json(data: bytes | str) -> t.Any:
    try:
        return json.loads(data)
    except (ValueError, TypeError) as ex:
        raise JsonError("Problem with decode json") from ex


def encode_json(data: t.Any) -> str:
    try:
        return json.dumps(data)
    except (ValueError, TypeError, OverflowError) as ex:
        raise JsonError("Problem with encode json") from ex


class BaseHttpSecurityPolicy(IHttpSecurityPolicy):
    def identify(self, request: Request) -> str:
        return ""

    def authenticated(self, request: Request) -> AuthInfo:
        return AuthInfo.create_anonymous()

    def permits(self, request: Request, permission: str) -> bool:
        return False

    def remember(self, request: Request, identity: str, **kw) -> None:
        pass

    def forget(self, request: Request, **kw) -> None:
        pass


class Cookies:
    def __init__(self) -> None:
        self._store: SimpleCookie[str] = SimpleCookie()

    def set(
        self,
        name: str,
        value: str,
        *,
        expires: str | None = None,
        domain: str | None = None,
        max_age: t.Union[int, str] | None = None,
        path: str = "/",
        secure: bool | None = None,
        httponly: bool | None = None,
        version: str | None = None,
        samesite: str | None = None,
    ) -> None:
        """
        Set or update cookie
        """
        assert name

        old = self._store.get(name)
        if old is not None and old.coded_value == "":
            self._store.pop(name)

        self._store[name] = value
        c = self._store[name]

        if expires is not None:
            c["expires"] = expires

        if domain is not None:
            c["domain"] = domain

        if max_age is not None:
            c["max-age"] = str(max_age)
        elif "max-age" in c:
            del c["max-age"]

        c["path"] = path

        if secure is not None:
            c["secure"] = secure
        if httponly is not None:
            c["httponly"] = httponly
        if version is not None:
            c["version"] = version
        if samesite is not None:
            c["samesite"] = samesite

    def remove(self, name: str):
        self.set(name, "", expires="Thu, 01 Jan 1970 00:00:00 GMT", max_age=0)

    def _populate(self, headers: CIMultiDict):
        for cookie in self._store.values():
            value = cookie.output(header="")[1:]
            headers.add("Set-Cookie", value)


def get_csrf(request: Request) -> ICsrf:
    try:
        return request[ODSS_HTTP_REQUEST_CSRF]
    except KeyError:
        raise RuntimeError("CSRF not found. Install CSRF Middleware in your app")
