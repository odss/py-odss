import logging

from ..core.consts import OBJECTCLASS, SERVICE_ID, SERVICE_RANKING
from .consts import SERVICE_SHELL_COMMAND
from .decorators import command
from .session import Session
from .utils import bundle_state_name, make_ascii_table


class Activator:
    def __init__(self):
        pass

    async def start(self, ctx):
        self.shell = ServiceShell(ctx)

        await ctx.register_service(SERVICE_SHELL_COMMAND, self.shell)

    async def stop(self, ctx):
        pass


class ServiceShell:
    def __init__(self, ctx):
        self.ctx = ctx

    @command("bl")
    def bundles_list(self, session: Session):
        """
        List all installed bundles
        """
        bundles = self.ctx.get_bundles()
        header = ("ID", "Name", "State", "Version")
        lines = [
            (bundle.id, bundle.name, bundle_state_name(bundle.state), bundle.version)
            for bundle in bundles
        ]
        return make_ascii_table("Bundles", header, lines)

    @command("bd")
    def bundle_details(self, session: Session, bundle_id: int):
        """
        Show bundle details
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            return f"Unknown bundle ID: {bundle_id}"

        buff = [
            "ID......: {0}".format(bundle.id),
            "Name....: {0}".format(bundle.name),
            "State...: {0}".format(bundle_state_name(bundle.state)),
            "Version.: {0}".format(bundle.version),
            "Location: {0}".format(bundle.location),
            "Published services:",
        ]
        refs = ["    {0}".format(ref) for ref in bundle.get_references()]
        if refs:
            buff.extend(refs)
        else:
            buff.append("    n/a")
        buff.append("Services using by bundle:")

        refs = ["    {0}".format(ref) for ref in bundle.get_using_services()]
        if refs:
            buff.extend(refs)
        else:
            buff.append("    n/a")

        return buff

    @command("sl")
    def services_list(self, session: Session, spec: str = None):
        """
        List all registred services
        """
        refs = self.ctx.get_service_references(spec)
        header = ("ID", "Classes", "Bundle", "Ranking")
        lines = [
            (
                str(ref.get_property(SERVICE_ID)),
                str(ref.get_property(OBJECTCLASS)),
                str(ref.get_bundle()),
                str(ref.get_property(SERVICE_RANKING)),
            )
            for ref in refs
        ]
        return make_ascii_table("Services", header, lines)

    @command("sd")
    def service_details(self, session: Session, service_id: int):
        """
        Show service details
        """
        ref = self.ctx.get_service_reference(None, {SERVICE_ID: int(service_id)})
        if not ref:
            return f"Service not found: {service_id}"

        props = ref.get_properties()
        lines = [
            "ID...........: {0}".format(props[SERVICE_ID]),
            "Classes......: {0}".format(props[OBJECTCLASS]),
            "Rank.........: {0}".format(props[SERVICE_RANKING]),
            "Bundle.......: {0}".format(ref.get_bundle()),
            "Properties...:",
        ]

        props = sorted(props.items())
        max_size = max([len(r[0]) for r in props], default=0)
        prop_format = f"    {{0:>{max_size}}} = {{1}}"
        for key, value in props:
            lines.append(prop_format.format(key, value))

        lines.append("Bundles using this service:")
        for bundle in ref.get_using_bundles():
            lines.append(f"    {bundle}")

        return lines

    @command("install")
    async def install_bundle(self, session: Session, name: str):
        """
        Install the bundle with the given name.
        """
        bundle = await self.ctx.install_bundle(name)
        return f"Bundle ID: {bundle.id}"

    @command("uninstall")
    async def uninstall_bundle(self, session: Session, bundle_id: int):
        """
        Uninstall the bundle with the given ID.
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            return f"Unknown bundle ID: {bundle_id}"
        else:
            session.write_line(
                f"Uninstalling [Bundle id={bundle.id} name={bundle.name}]"
            )
            await bundle.uninstall()

    @command("start")
    async def start_bundle(self, session: Session, bundle_id: int):
        """
        Start the bundle with the given ID.
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            return "Unknown bundle ID: {bundle_id}"

        session.write_line(f"Starting [Bundle id={bundle.id} name={bundle.name}]")
        await bundle.start()

    @command("stop")
    async def stop_bundle(self, session: Session, bundle_id: int):
        """
        Stop the bundle with the given ID.
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            return f"Unknown bundle ID: {bundle_id}"

        session.write_line(f"Stoping [Bundle id={bundle.id} name={bundle.name}]")
        await bundle.stop()

    @command()
    def properties(self, session: Session):
        """
        List of all properties
        """
        properties = self.ctx.get_framework().get_properties().items()
        lines = [item for item in properties]
        return make_ascii_table("Properties", ["Property name", "Value"], lines)

    @command()
    def log_level(self, session: Session, level: str = None, name: str = None):
        """
        Prints/Changes log level
        """
        logger = logging.getLogger(name)
        if not name:
            name = "root"

        if not level:
            level = logging.getLevelName(logger.getEffectiveLevel())
            real_level = logging.getLevelName(logger.level)
            session.write_line(f"{name} log level: {level} (real: {real_level})")
        else:
            try:
                logger.setLevel(level.upper())
                session.write_line(f"New level for {name}: {level}")
            except ValueError:
                session.write_line(f"Invalid log level: {level}")
