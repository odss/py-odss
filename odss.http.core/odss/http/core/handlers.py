import asyncio
import logging
import typing as t

from odss.http.common import (
    Response,
    JsonResponse,
    JSONError,
    HTTPException,
)

from .deps import RequestValidationError, get_dependency, resolve_dependency
from .encoders import serialize_response

logger = logging.getLogger(__name__)


class ViewSettings(t.TypedDict):
    prefix: str


def create_request_handler(path, props, handler) -> t.Callable:
    deps = get_dependency(path, handler)

    async def request_handler(request):
        try:
            values, errors = await resolve_dependency(deps, request, props)
            if errors:
                raise RequestValidationError(errors)
        except JSONError as ex:
            raise HTTPException("There was an error parsing the body") from ex
        else:
            response = handler(**values)
            if asyncio.iscoroutine(response):
                response = await response
            if not isinstance(response, Response):
                response = JsonResponse(body=serialize_response(response))
            return response

    return request_handler
