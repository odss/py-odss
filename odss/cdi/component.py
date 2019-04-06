import asyncio
import logging
import typing as t

from odss.core.bundle import BundleContext

from .contexts import ComponentContext
from .interfaces import IHandler, IComponentManager


logger = logging.getLogger(__name__)


class ComponentManager(IComponentManager):

    VALID = "valid"

    INVALID = "invalid"

    STOPED = "stoped"

    def __init__(
        self, context: ComponentContext, handlers: t.Iterable[IHandler]
    ) -> None:
        self.state = ComponentManager.INVALID
        self.context = context
        self.__handlers = handlers
        self._requirements = None

    def get_instance(self):
        if self.__instance is None:
            raise TypeError("Not created component instance")
        return self.__instance

    def get_bundle_context(self) -> BundleContext:
        return self.context.get_bundle_context()

    async def start(self):
        await self.__safe_handlers_callback("start")
        await self.check_lifecycle()

    async def stop(self):
        await self.invalidate()
        await self.__safe_handlers_callback("stop")
        self.state = ComponentManager.STOPED

    def set_requirements(self, requirements):
        if self._requirements is not None:
            raise TypeError("Requirements already setup")
        self._requirements = requirements

    def reset_requirements(self):
        self._requirements = None

    async def check_lifecycle(self):
        was_valid = self.state == ComponentManager.VALID

        is_valid = await self.__safe_handlers_callback("is_valid", break_on_false=True)
        if was_valid and not is_valid:
            await self.invalidate()
        elif is_valid:
            await self.validate()

    async def validate(self):
        await self.__safe_handlers_callback("pre_validate")

        args = self._requirements if self._requirements is not None else []
        self.__instance = self.context.factory_class(*args)

        self.state = ComponentManager.VALID

        await self.__safe_handlers_callback("post_validate")

    async def invalidate(self):
        await self.__safe_handlers_callback("pre_invalidate")

        self.state = ComponentManager.INVALID
        self.__instance = None

        await self.__safe_handlers_callback("post_invalidate")

    async def __safe_handlers_callback(self, method_name, *args, **kwargs):
        break_on_false = kwargs.pop("break_on_false", False)
        result = True
        for handler in self.__handlers:
            try:
                method = getattr(handler, method_name)
            except AttributeError:
                pass
            else:
                try:
                    async_method = asyncio.coroutine(method)
                    res = await async_method(*args, **kwargs)
                    if res is not None and not res:
                        result = False
                        if break_on_false:
                            break
                except Exception as ex:
                    # Log errors
                    logger.exception("Error calling handler '%s': %s", handler, ex)

        return result
