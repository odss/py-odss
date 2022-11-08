import argparse
import asyncio
import logging

from odss.common import make_ascii_table
from odss.core import __version__, Framework


from .config import load_config


def set_uv_loop() -> None:
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        logging.warning("Missing uvloop")


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ODSS :: OSGi in python async version")
    parser.add_argument("--version", action="version", version=__version__)

    group = parser.add_argument_group("Framework options")
    group.add_argument(
        "-d",
        nargs="+",
        dest="properties",
        metavar="KEY=VALUE",
        help="Sets of properties",
    )
    group.add_argument(
        "--entry-points",
        action="store_true",
        dest="include_entry_points",
        help="Include all bundles founded in entry points",
    )

    group.add_argument(
        "-b",
        "--bundle",
        nargs="+",
        action="extend",
        dest="bundles",
        help="Sets of bundles",
    )
    group.add_argument(
        "--shell",
        action="store_true",
        help="Enable with repr",
    )
    group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Set loggers to DEBUG level",
    )
    group.add_argument(
        "--debug-loop",
        action="store_true",
        help="Set debug to loop",
    )
    return parser.parse_args()


def handle_args(args):
    print(args)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    set_uv_loop()

    config = load_config(
        include_entry_points=args.include_entry_points, debug=args.verbose
    )
    for prop in args.properties or []:
        key, value = prop.split("=", 1)
        config.properties[key] = value

    config.bundles.extend(args.bundles or [])
    if args.shell:
        config.bundles.extend(
            [
                "odss.services.shell",
                "odss.services.shell.commands",
                "odss.services.terminal",
            ]
        )
    config.normalize()
    return config


async def setup_and_run_odss(config):
    if config.debug:
        print(
            make_ascii_table(
                "Properties",
                ["Key", "Value"],
                [(name, str(value)) for name, value in config.properties.items()],
            )
        )

    framework = Framework(config.properties)
    # await asyncio.gather(*[
    #     asyncio.create_task(
    #         framework.install_bundle(bundle_name),
    #         name=bundle_name
    #     )
    #     for bundle_name in config.bundles
    # ])
    for bundle_name in config.bundles:
        await framework.install_bundle(bundle_name)

    try:
        await framework.start(True)
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.create_task(framework.stop())


def main():
    args = get_arguments()
    config = handle_args(args)
    asyncio.run(setup_and_run_odss(config), debug=True)


if __name__ == "__main__":
    main()
