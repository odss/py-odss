import argparse
import asyncio
import os
import sys
import threading

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
    return parser.parse_args()


def ensure_config_path(config_dir: str) -> None:
    if not os.path.isdir(config_dir):
        try:
            os.mkdir(config_dir)
        except OSError:
            print("Unable to create configuration directory: {}".format(config_dir))
            sys.exit(1)


async def setup_and_run_odss(config_dir):
    framework = Framework({"http.server.host": "127.0.0.1", "http.server.port": 8080})

    await framework.install_bundle("odss.http.server")
    await framework.start(True)


def main() -> int:
    set_uv_loop()

    # args = get_arguments()

    config_dir = os.path.join(os.getcwd(), consts.CONFIG_DIR_NAME)
    ensure_config_path(config_dir)

    exit_code = asyncio.run(setup_and_run_odss(config_dir))

    return exit_code


if __name__ == "__main__":
    main()
