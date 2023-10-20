import http
import typing as t
from http.cookies import SimpleCookie

try:
    import ujson as json
except ImportError:
    import json  # type: ignore[no-redef]

from odss.http.common.abc import AuthInfo, IHttpContext, IHttpSecurityPolicy


class JsonError(Exception):
    pass


def decode_json(data: str) -> t.Any:
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
    def identify(self, ctx: IHttpContext) -> str:
        return ""

    def authenticated(self, ctx: IHttpContext) -> AuthInfo:
        return AuthInfo.create_anonymous()

    def permits(self, ctx: IHttpContext, permission: str) -> bool:
        return False

    def remember(self, ctx: IHttpContext, identity: str, **kw) -> None:
        pass

    def forget(self, ctx: IHttpContext, **kw) -> None:
        pass


BodyType = str | bytes
HeadersType = dict[str, str]


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

    def _populate(self, headers):
        for cookie in self._store.values():
            value = cookie.output(header="")[1:]
            headers.append(("Set-Cookie", value))


class Response:
    content_type = None
    charset = "utf-8"

    def __init__(
        self,
        body: BodyType,
        *,
        code: int = 200,
        headers: dict[str, str] | None = None,
        content_type: str | None = None,
        charset: str | None = None,
    ) -> None:
        self.cookies = Cookies()
        if content_type is not None:
            match content_type:
                case "json":
                    content_type = "application/json"
                case "text":
                    content_type = "text/plain"
                case "html":
                    content_type = "text/html"

            self.content_type = content_type
        if charset is not None:
            self.charset = charset
        self.code = code
        self.body = self.prepare_body(body)

        if headers is None:
            headers = {}
        elif isinstance(headers, list):
            headers = dict(headers)
        self.headers = headers

    def prepare_body(self, body: BodyType):
        if body is None:
            return ""
        if isinstance(body, bytes):
            return body
        return body.encode(self.charset)

    def finish(self):
        self.cookies._populate(self.headers)


class HtmlResponse(Response):
    content_type = "text/html"


class PlainTextResponse(Response):
    content_type = "text/plain"


class JsonResponse(Response):
    content_type = "application/json"

    def prepare_body(self, body: BodyType):
        return encode_json(body)


class RedirectResponse(Response):
    def __init__(
        self,
        location: str,
        code: int,
        *,
        headers: dict[str, str] | None = None,
        text: str = None,
        charset: str = None,
    ) -> None:
        assert location  # raise ValueError?
        headers = headers if headers is not None else {}
        headers["Location"] = location
        super().__init__(text, code=code, headers=headers, charset=charset)
