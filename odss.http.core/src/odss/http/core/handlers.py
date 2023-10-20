import asyncio
import logging
import typing as t

from odss.http.common import JsonResponse, Request, Response

from .deps import get_dependency, resolve_dependency
from .encoders import serialize_response

logger = logging.getLogger(__name__)


class ViewSettings(t.TypedDict):
    prefix: str


def create_request_handler(path, props, handler) -> t.Callable:
    deps = get_dependency(path, handler)

    async def request_handler(request: Request):
        values = await resolve_dependency(deps, request, props)
        response = handler(**values)
        if asyncio.iscoroutine(response):
            response = await response
        if not isinstance(response, Response):
            response = JsonResponse(body=serialize_response(response))
        return response

    return request_handler
