import logging
from odss.services.configadmin import (
    IConfigurationManaged,
    IConfigurationManagedFactory,
)
from odss.services.configadmin.consts import SERVICE_FACTORY_PID, SERVICE_PID


class Log:
    async def updated(self, props):
        print(f"Log.updateds({props})")
        if props:
            level = props.get("level")
            if level:
                logging.getLogger().setLevel(level)


class SocketFactory:
    async def updated(self, pid, props):
        print(f"SocketFactory.update({pid}, {props})")

    async def deleted(self, pid: str):
        print(f"SocketFactory.deleted({pid})")


class Activator:
    async def start(self, ctx):
        PID = "l"
        FPID = "sf"
        ctx.register_service(IConfigurationManaged, Log(), {SERVICE_PID: PID})
        ctx.register_service(
            IConfigurationManagedFactory, SocketFactory(), {SERVICE_FACTORY_PID: FPID}
        )
        # ref = ctx.get_service_reference('odss.services.ConfigAdmin')
        # admin_config = ctx.get_service(ref)
        # config = await admin_config.get_configuration(PID)
        # await config.update({'level': 'DEBUG'})
        # await config.update({})

    async def stop(self, ctx):
        pass
