import logging
from odss.common import (
    SERVICE_FACTORY_PID,
    SERVICE_PID,
    IConfigurationManaged,
    IConfigurationManagedFactory,
)


class Log:
    async def updated(self, props):
        print(f"Log::updated({props})")
        if props:
            level = props.get("level")
            if level:
                logging.getLogger().setLevel(level)


PID = "logger"


class Activator:
    async def start(self, ctx):
        await ctx.register_service(IConfigurationManaged, Log(), {SERVICE_PID: PID})

    async def stop(self, ctx):
        pass
