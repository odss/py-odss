import typing as t

from multidict import CIMultiDict

from .base import encode_json, Cookies

BodyType = str | bytes | None
HeadersType = t.Mapping[str, str] | list[tuple[str, str]]


class Response:
    content_type = None
    charset = "utf-8"

    def __init__(
        self,
        body: BodyType,
        *,
        code: int = 200,
        headers: HeadersType | None = None,
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
        self.headers: CIMultiDict[str] = (
            CIMultiDict(headers) if headers is not None else CIMultiDict()
        )

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
        headers: HeadersType | None = None,
        text: str | None = None,
        charset: str | None = None,
    ) -> None:
        assert location  # raise ValueError?
        headers = [("Location", location)]
        super().__init__(text, code=code, headers=headers, charset=charset)
