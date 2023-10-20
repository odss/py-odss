from http import HTTPStatus

from .base import Cookies

Headers = dict[str, str]

__all__ = (
    "HttpRedirect",
    "HttpFound",
    "HttpSeeOther",
    "HttpUseProxy",
    "HttpNotModified",
    "HttpMultipleChoices",
    "HttpMovedPermanently",
    "HttpTemporaryRedirect",
    "HttpPermanentRedirect",
)


class HttpError(Exception):
    status_code = -1
    default_reason = ""

    def __init__(
        self,
        reason: str | None = None,
        *,
        headers: Headers | None = None,
        code: int | None = None,
        status: str | None = None,
        content_type: str | None = None,
        charset: str | None = None,
    ) -> None:
        super().__init__()
        self.reason = reason if reason is not None else ""
        self.code = code if code is not None else self.status_code
        if status is None:
            status = HTTPStatus(self.code).phrase
        self.status = status
        self.charset = charset or "utf-8"
        self.reason = reason if reason is not None else self.default_reason
        if headers is None:
            headers = {}
        elif isinstance(headers, list):
            headers = dict(headers)
        self.headers = headers
        if content_type is None:
            content_type = "application/json"
        self.content_type = content_type

    def to_json(self):
        error = {
            "code": self.code,
            "status": self.status,
        }
        if self.reason:
            error["reason"] = self.reason
        return error

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(code={self.code!r}, status={self.status!r} reason={self.reason!r})"


class HttpRedirect(HttpError):
    def __init__(
        self,
        location: str,
        *,
        reason: str | None = None,
        code: int | None = None,
        status: str | None = None,
        headers: Headers | None = None,
        content_type: str | None = None,
        charset: str = "utf-8",
    ):
        super().__init__(
            reason=reason,
            code=code,
            status=status,
            content_type=content_type,
            headers=headers,
            charset=charset,
        )
        if not location:
            raise ValueError("Require location to redirect")
        self.headers["Location"] = location


class HttpMultipleChoices(HttpRedirect):
    status_code = 300


class HttpMovedPermanently(HttpRedirect):
    status_code = 301


class HttpFound(HttpRedirect):
    status_code = 302


class HttpSeeOther(HttpRedirect):
    status_code = 303


class HttpNotModified(HttpRedirect):
    status_code = 304


class HttpUseProxy(HttpRedirect):
    status_code = 305


class HttpTemporaryRedirect(HttpRedirect):
    status_code = 307


class HttpPermanentRedirect(HttpRedirect):
    status_code = 308


class BadRequestError(HttpError):
    status_code = 400
    default_reason = "The request could not be processed"


class UnauthorizedError(HttpError):
    status_code = 401
    default_reason = "The request could not be authorized"


class UnprocessableContentError(HttpError):
    status_code = 422
    default_reason = "The request was malformed or contained invalid parameters"
