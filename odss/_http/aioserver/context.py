import typing as t

from aiohttp import web

from ..abc import IHttpContext

try:
    import ujson as json
except ImportError:
    import json


class HttpContext(IHttpContext):
    def __init__(self, request: web.Request):
        self._request = request
        self.state = {}

    @property
    def request(self):
        return self._request

    # method
    # secure
    # scheme
    # version
    # host
    # remote
    # url
    # path
    # path_qs
    # headers
    # raw_headers
    def __getattr__(self, key: str) -> t.Any:
        return getattr(self._request, key)

    async def json(self):
        body = await self._request.read()
        return json.loads(body)

    def body(self):
        return self._request.read()

    def text(self):
        return self._request.text()

    def response(
        self,
        body,
        status: int = 200,
        *,
        headers: t.Optional[t.Dict] = None,
        content_type: str = None,
        charset: t.Optional[str] = None
    ):
        if isinstance(body, str):
            body = body.encode("utf-8")
        if content_type == "json":
            content_type = "application/json"

        return web.Response(
            body=body,
            status=status,
            headers=headers,
            content_type=content_type,
            charset=charset,
        )

    def json_response(
        self, data: t.Any, status: int = 200, *, headers: t.Optional[t.Dict] = None
    ):
        return self.response(
            json.dumps(data), status, content_type="json", headers=headers
        )

    def __getitem__(self, key: str) -> t.Any:
        return self._state[key]

    def __setitem__(self, key: str, value: t.Any) -> None:
        self._state[key] = value

    def __delitem__(self, key: str) -> None:
        del self._state[key]

    def __len__(self) -> int:
        return len(self._state)

    def __iter__(self) -> t.Iterator[str]:
        return iter(self._state)
