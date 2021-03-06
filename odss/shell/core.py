from ..core.consts import SERVICE_ID, OBJECTCLASS, SERVICE_RANKING
from . import SERVICE_SHELL, SERVICE_SHELL_COMMAND
from .shell import Shell
from .utils import make_ascii_table, bundle_state_name


class Activator:
    def __init__(self):
        pass

    async def start(self, ctx):
        print(f"{__name__} Activator::start()")
        self.shell = ServiceShell(ctx)
        ctx.add_service_listener(self, SERVICE_SHELL_COMMAND)

        await ctx.register_service(SERVICE_SHELL, self.shell)
        print(f"{__name__} Activator::start() ::post")

    async def stop(self, ctx):
        print(f"{__name__} Activator::stop()")

        print(f"{__name__} Activator::stop() ::post")

    async def service_changed(self, event):
        print(f"service_changed({event})")


class ServiceShell(Shell):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.register_command("bl", self.bundles_list)
        self.register_command("bd", self.bundle_details)
        self.register_command("sl", self.services_list)
        self.register_command("sd", self.service_details)
        self.register_command("install", self.install_bundle)
        self.register_command("uninstall", self.uninstall_bundle)
        self.register_command("start", self.start_bundle)
        self.register_command("stop", self.stop_bundle)

    def bind_command(self):
        pass

    def unbind_command(self):
        pass

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
        output = make_ascii_table(header, lines)
        session.write_line(output)

    def bundle_details(self, session, bundle_id):
        """
        Show bundle details
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            session.write_line("Unknown bundle ID: {0}", bundle_id)
            return False

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

        session.write_line("\n".join(buff))

    def services_list(self, session, spec=None):
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
        output = make_ascii_table(header, lines)
        session.write_line(output)

    def service_details(self, session, service_id):
        """
        Show service details
        """
        ref = self.ctx.get_service_reference(None, {SERVICE_ID: int(service_id)})
        if not ref:
            session.write_line(f"Service not found: {service_id}")
            return False
        props = ref.get_properties()
        buff = [
            "ID...........: {0}".format(props[SERVICE_ID]),
            "Classes......: {0}".format(props[OBJECTCLASS]),
            "Rank.........: {0}".format(props[SERVICE_RANKING]),
            "Bundle.......: {0}".format(ref.get_bundle()),
            "Properties...:",
        ]
        for key, value in sorted(props.items()):
            buff.append(f"    {key} = {value}")

        buff.append("Bundles using this service:")
        for bundle in ref.get_using_bundles():
            buff.append(f"    {bundle}")

        session.write_line("\n".join(buff))

    async def install_bundle(self, session, name):
        """
        Install the bundle with the given name.
        """
        bundle = await self.ctx.install_bundle(name)
        session.write_line("Bundle ID: {0}".format(bundle.id))
        return bundle.id

    async def uninstall_bundle(self, session, bundle_id):
        """
        Uninstall the bundle with the given ID.
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            session.write_line("Unknown bundle ID: {0}", bundle_id)
            return False
        session.write_line(
            "Uninstalling [Bundle id={0} name={1}]".format(bundle.id, bundle.name)
        )
        await bundle.uninstall()

    async def start_bundle(self, session, bundle_id):
        """
        Start the bundle with the given ID.
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            session.write_line("Unknown bundle ID: {0}", bundle_id)
            return False
        session.write_line(
            "Starting [Bundle id={0} name={1}]".format(bundle.id, bundle.name)
        )
        await bundle.start()

    async def stop_bundle(self, session, bundle_id):
        """
        Stop the bundle with the given ID.
        """
        bundle = self.ctx.get_bundle(int(bundle_id))
        if bundle is None:
            session.write_line("Unknown bundle ID: {0}", bundle_id)
            return False
        session.write_line(
            "Stoping [Bundle id={0} name={1}]".format(bundle.id, bundle.name)
        )
        await bundle.stop()
