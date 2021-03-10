import argparse
import asyncio
import os
import json
import logging

from odss import consts
from odss.core.framework import Framework


def set_uv_loop() -> None:
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        print("Missing uvloop")


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ODSS :: OSGi in python async version")
    parser.add_argument("--version", action="version", version=consts.__version__)

    group = parser.add_argument_group("Framework options")
    group.add_argument(
        "-d",
        nargs="+",
        dest="properties",
        metavar="KEY=VALUE",
        help="Sets framework properties",
    )
    group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Set loggers to DEBUG level",
    )

    return parser.parse_args()


def handle_args(args):
    set_uv_loop()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
    config = ConfigLoader(debug=args.verbose)

    for prop in args.properties or []:
        key, value = prop.split("=", 1)
        config.properties[key] = value

    return config


class ConfigLoader:
    DEFAULT_PATH = (
        "/etc/default",
        "/etc",
        "/usr/local/etc",
        "~/.local/odss",
        "~",
        ".",
    )
    DEFAULT_FILE = "odss.json"

    def __init__(self, debug: bool = False):
        self.properties = {}
        self.bundles = []
        self.debug = debug
        self.load()

    def load(self, file_path: str = None):
        if file_path is not None:
            logging.info("Load config: %s", file_path)
            with open(file_path, "r") as fh:
                self.extend(json.load(fh))
        else:
            for file_path in self._find_default_configs():
                self.load(file_path)

    def extend(self, config):
        self.bundles.extend(config.get("bundles", []))
        self.properties.update(config.get("properties", {}))

    def _find_default_configs(self):
        for dir_path in self.DEFAULT_PATH:
            dir_path = os.path.expanduser(dir_path)
            full_name = os.path.join(dir_path, self.DEFAULT_FILE)
            if os.path.exists(full_name):
                yield full_name


async def setup_and_run_odss(config):
    if config.debug:
        print(config.properties)

    framework = Framework(config.properties)
    for bundle_name in config.bundles:
        await framework.install_bundle(bundle_name)
    await framework.start(True)


def main():

    args = get_arguments()
    config = handle_args(args)
    config.bundles.extend(
        ["odss.shell.core", "odss.shell.service", "odss.shell.console"]
    )
    try:
        asyncio.run(setup_and_run_odss(config), debug=config.debug)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
