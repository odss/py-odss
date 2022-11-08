import logging

from odss.common import (
    command,
    make_ascii_table,
    SERVICE_SHELL_COMMANDS,
    OBJECTCLASS,
    SERVICE_ID,
    SERVICE_PRIORITY,
    SERVICE_BUNDLE_ID,
)

from .utils import bundle_state_name


class Activator:
    def __init__(self):
        pass

    async def start(self, ctx):
        self.shell = BasicComands(ctx)
        await ctx.register_service(SERVICE_SHELL_COMMANDS, self.shell)

    async def stop(self, ctx):
        pass


class BasicComands:
    def __init__(self, ctx):
        self.ctx = ctx

    @command("bl")
    def bundles_list(self, session):
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
    def bundle_details(self, session, bundle_id: int):
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
            # "Location: {0}".format(bundle.location),
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
    def services_list(self, session, spec: str = None):
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
                str(ref.get_property(SERVICE_PRIORITY)),
            )
            for ref in refs
        ]
        return make_ascii_table("Services", header, lines)

    @command("sd")
    def service_details(self, session, service_id: int):
        """
        Show service details
        """
        ref = self.ctx.get_service_reference(None, {SERVICE_ID: int(service_id)})
        if not ref:
            return f"Service not found: {service_id}"

        excludes = (SERVICE_ID, SERVICE_PRIORITY, OBJECTCLASS, SERVICE_BUNDLE_ID)
        props = ref.get_properties()
        lines = [
            "ID...........: {0}".format(props[SERVICE_ID]),
            "Classes......: {0}".format(props[OBJECTCLASS]),
            "Rank.........: {0}".format(props[SERVICE_PRIORITY]),
            "Bundle.......: {0}".format(ref.get_bundle()),
            "Properties...:",
        ]
        props = sorted(
            (key, value) for key, value in props.items() if key not in excludes
        )
        max_size = max([len(r[0]) for r in props], default=0)
        prop_format = f"    {{0:>{max_size}}} = {{1}}"
        lines.extend([prop_format.format(key, value) for key, value in props])

        lines.append("Bundles using this service:")
        bundles = ref.get_using_bundles()
        if len(bundles):
            for bundle in ref.get_using_bundles():
                lines.append(f"    {bundle}")
        else:
            lines.append("    n/a")

        return lines

    @command("install")
    async def install_bundle(self, session, name: str):
        """
        Install the bundle with the given name.
        """
        bundle = await self.ctx.install_bundle(name)
        return f"Bundle ID: {bundle.id}"

    @command("uninstall")
    async def uninstall_bundle(self, session, bundle_id: int):
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
    async def start_bundle(self, session, bundle_id: int):
        """
        Start the bundle with the given ID.
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            return "Unknown bundle ID: {bundle_id}"

        session.write_line(f"Starting [Bundle id={bundle.id} name={bundle.name}]")
        await bundle.start()

    @command("stop")
    async def stop_bundle(self, session, bundle_id: int):
        """
        Stop the bundle with the given ID.
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            return f"Unknown bundle ID: {bundle_id}"

        session.write_line(f"Stoping [Bundle id={bundle.id} name={bundle.name}]")

        await bundle.stop()

    @command("reload")
    async def reload_bundle(self, session, bundle_id: int):
        """
        Reload the bundle with the given ID.
        """

        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            return "Unknown bundle ID: {bundle_id}"

        session.write_line(f"Reload [Bundle id={bundle.id} name={bundle.name}]")
        await bundle.uninstall()
        bundle = await self.ctx.framework.install_bundle(bundle.name)
        await bundle.start()

    @command()
    def properties(self, session):
        """
        List of all properties
        """
        properties = self.ctx.get_framework().get_properties().items()
        lines = [(name, str(value)) for name, value in properties]
        return make_ascii_table("Properties", ["Property name", "Value"], lines)

    @command()
    def log_level(self, session, level: str = None, name: str = None):
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
