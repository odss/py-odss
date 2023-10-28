from typing_extensions import TypedDict

SECRET_LENGTH = 32
REQUEST_NEW_TOKEN_KEY = "newcrsftoken"
PROTECTED_METHODS = ("POST", "PUT", "UPDATE", "DELETE")


CookieParams = TypedDict(
    "CookieParams",
    {
        "name": str,
        "max_age": int,
        "domain": str | None,
        "path": str,
        "secure": bool,
        "httponly": bool,
        "samesite": str,
    },
    total=False,
)

DEFAULT_COOKIE_PARAMS: CookieParams = {
    "max_age": 31536000,  # one year in seconds
    "domain": None,
    "path": "/",
    "secure": False,
    "httponly": True,
    "samesite": "Lex",
}
