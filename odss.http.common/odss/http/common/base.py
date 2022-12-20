import typing as t
import http

try:
    import ujson as json
except ImportError:
    import json  # type: ignore[no-redef]

from .abc import AuthInfo, IHttpContext, IHttpSecurityPolicy


class JSONError(Exception):
    pass


def decode_json(data: str) -> t.Any:
    try:
        return json.loads(data)
    except (ValueError, TypeError) as ex:
        raise JSONError("Problem with decode json") from ex


def encode_json(data: t.Any) -> str:
    try:
        return json.dumps(data)
    except (ValueError, TypeError, OverflowError) as ex:
        raise JSONError("Problem with encode json") from ex


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


class Response:
    content_type = None
    charset = "utf-8"

    def __init__(
        self,
        body: BodyType,
        *,
        status: int = 200,
        headers: dict[str, str] | None = None,
        content_type: str | None = None,
        charset: str | None = None,
    ) -> None:
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
        self.status = status
        self.body = self.prepare_body(body)
        self.headers = headers

    def prepare_body(self, body: BodyType):
        if body is None:
            return ""
        if isinstance(body, bytes):
            return body
        return body.encode(self.charset)


class HTMLResponse(Response):
    content_type = "text/html"


class PlainTextResponse(Response):
    content_type = "text/plain"


class JsonResponse(Response):
    content_type = "application/json"

    def prepare_body(self, body: BodyType):
        return encode_json(body)


class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str | None = None,
        # status: str | None = "unknown",
        headers: dict | None = None,
    ) -> None:
        if detail is None:
            detail = http.HTTPStatus(status_code).phrase
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

    def serialize(self):
        return {
            "error": {
                "code": self.status_code,
                # "status": "",
                "message": self.detail,
            }
        }

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"
