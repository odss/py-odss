import argparse
import asyncio
import logging

from odss import consts
from odss.core import Framework
from odss.shell.utils import make_ascii_table

from .config import ConfigLoader


def set_uv_loop() -> None:
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        logging.warning("Missing uvloop")


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ODSS :: OSGi in python async version")
    parser.add_argument("--version", action="version", version=consts.__version__)

    group = parser.add_argument_group("Framework options")
    group.add_argument(
        "-d",
        nargs="+",
        dest="properties",
        metavar="KEY=VALUE",
        help="Sets of properties",
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

    return parser.parse_args()


def handle_args(args):
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    set_uv_loop()

    config = ConfigLoader(debug=args.verbose)
    for prop in args.properties or []:
        key, value = prop.split("=", 1)
        config.properties[key] = value

    config.bundles.extend(args.bundles or [])
    if args.shell:
        config.bundles.extend(
            ["odss.shell.core", "odss.shell.service", "odss.terminal.main"]
        )
    config.normalize()
    return config


async def setup_and_run_odss(config):
    if config.debug:
        print(
            make_ascii_table("Properties", ["Key", "Value"], config.properties.items())
        )

    framework = Framework(config.properties)
    for bundle_name in config.bundles:
        await framework.install_bundle(bundle_name)
    await framework.start(True)


def main():

    args = get_arguments()
    config = handle_args(args)
    try:
        asyncio.run(
            setup_and_run_odss(config),
            # debug=config.debug
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
