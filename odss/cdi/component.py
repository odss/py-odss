import asyncio
import logging
import typing as t

from odss.core.bundle import BundleContext

from .consts import CALLBACK_INVALIDATE, CALLBACK_VALIDATE
from .contexts import ComponentContext
from .interfaces import IComponentManager, IHandler

logger = logging.getLogger(__name__)


class ComponentManager(IComponentManager):

    VALID = "valid"

    INVALID = "invalid"

    STOPED = "stoped"

    def __init__(
        self, context: ComponentContext, handlers: t.Iterable[IHandler]
    ) -> None:
        self._state = ComponentManager.INVALID
        self._context = context
        self._handlers = handlers
        self._requirements = None

    @property
    def context(self):
        return self._context

    def get_instance(self):
        if self._instance is None:
            raise TypeError("Not created component instance")
        return self._instance

    def get_bundle_context(self) -> BundleContext:
        return self._context.get_bundle_context()

    async def start(self):
        await self.__handlers_callback("start")
        await self.check_lifecycle()

    async def stop(self):
        await self.invalidate()
        await self.__handlers_callback("stop")
        self._state = ComponentManager.STOPED

    async def invoke(self, method, service, reference):
        async_handler_callback = asyncio.coroutine(method)
        await async_handler_callback(self, service)

    def set_requirements(self, requirements):
        if self._requirements is not None:
            raise TypeError("Requirements already setup")
        self._requirements = requirements

    def reset_requirements(self):
        self._requirements = None

    async def check_lifecycle(self):
        was_valid = self._state == ComponentManager.VALID

        is_valid = await self.__handlers_callback("is_valid", break_on_false=True)
        if was_valid and not is_valid:
            await self.invalidate()
        elif is_valid:
            await self.validate()

    async def validate(self):
        await self.__handlers_callback("pre_validate")

        args = self._requirements if self._requirements is not None else []
        self._instance = self._context.factory_class(*args)
        await self.__validation_callback(CALLBACK_VALIDATE)
        self._state = ComponentManager.VALID

        await self.__handlers_callback("post_validate")

    async def invalidate(self):
        await self.__handlers_callback("pre_invalidate")
        await self.__validation_callback(CALLBACK_INVALIDATE)
        self._state = ComponentManager.INVALID
        self._instance = None
        await self.__handlers_callback("post_invalidate")

    async def __handlers_callback(self, method_name, *args, **kwargs):
        break_on_false = kwargs.pop("break_on_false", False)
        result = True
        for handler in self._handlers:
            try:
                handler_callback = getattr(handler, method_name)
            except AttributeError:
                pass
            else:
                try:
                    async_handler_callback = asyncio.coroutine(handler_callback)
                    res = await async_handler_callback(*args, **kwargs)
                    if res is not None and not res:
                        result = False
                        if break_on_false:
                            break
                except Exception as ex:
                    # Log errors
                    logger.exception("Error calling handler '%s': %s", handler, ex)

        return result

    async def __validation_callback(self, kind: str):
        callback, args = self._context.get_callback(kind)
        if not callback:
            return True
        try:
            async_callback = asyncio.coroutine(callback)
            await async_callback(self._instance, self._context.get_bundle_context())
        except Exception as ex:
            logger.exception(
                "Error calling @Validate/@Invalidate method '%s': %s", kind, ex
            )
