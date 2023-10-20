import argparse
import asyncio
import logging
from .helpers import GracefulExit, cancel_tasks, register_signal_handling

from odss.common import make_ascii_table
from odss.core import Framework, __version__

from .config import load_config
from .reloader import Reloader


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
    group.add_argument(
        "--watch",
        action="store_true",
        help="Watch file modification to reload app",
    )
    return parser.parse_args()


def handle_args(args):
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    set_uv_loop()

    config = load_config(
        include_entry_points=args.include_entry_points, watch=args.watch
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


async def run_framework(config):
    framework = Framework(config.properties)
    # await asyncio.gather(*[
    #     asyncio.create_task(
    #         framework.install_bundle(bundle_name),
    #         name=bundle_name
    #     )
    #     for bundle_name in config.bundles
    # ])
    register_signal_handling(framework)

    for bundle_info in config.bundles:
        bundle = await framework.install_bundle(bundle_info["location"])
        if "startlevel" in bundle_info:
            bundle.start_level = bundle_info["startlevel"]

    reloader = Reloader(framework)
    try:
        if config.watch:
            await reloader.start()
        await framework.start()

        while True:
            await asyncio.sleep(10)
    finally:
        await reloader.stop()
        await framework.stop()


def main():
    args = get_arguments()
    config = handle_args(args)

    if config.debug:
        print(
            make_ascii_table(
                "Properties",
                ["Key", "Value"],
                [(name, str(value)) for name, value in config.properties.items()],
            )
        )
    loop = asyncio.new_event_loop()

    main_task = loop.create_task(run_framework(config))
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_task)
    except (GracefulExit, KeyboardInterrupt) as ex:
        pass
    finally:
        cancel_tasks({main_task}, loop)
        cancel_tasks(asyncio.all_tasks(loop), loop)
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


if __name__ == "__main__":
    main()
