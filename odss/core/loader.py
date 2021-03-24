import asyncio
import contextlib
import importlib
import json
import logging
import os
import pathlib
import subprocess
import sys
import typing as t
from importlib.metadata import PackageNotFoundError, version

import pkg_resources

logger = logging.getLogger(__name__)

pip_lock = asyncio.Lock()


async def load_bundle(runner, name: str, path: str = None):
    integration = await runner.create_job(Integration.load, name, path)
    if integration.requirements:
        await process_requirements(runner, name, integration.requirements)
    return integration


def import_module(name: str, path: str = None):
    logger.debug("Import module: %s with path: %s", name, path)
    try:
        with sys_path(path):
            module = importlib.import_module(name)
            return module
    except ImportError as ex:
        raise RuntimeError("Error installing bundle '{0}': {1}".format(name, ex))


def unload_bundle(name):
    try:
        del sys.modules[name]
    except KeyError:
        pass


@contextlib.contextmanager
def sys_path(path):
    try:
        if path:
            sys.path.insert(0, path)
        yield
    finally:
        if path:
            sys.path.remove(path)


Manifest = t.TypedDict(
    "Manifest", {"references": t.List[str], "requirements": t.List[str]}
)


def is_package(module) -> bool:
    return hasattr(module, "__path__")


class Integration:
    @classmethod
    def load(cls, name: str, include_path: str = None):
        module = import_module(name, include_path)
        manifest = None
        if is_package(module):  # package
            for base in module.__path__:
                manifest_path = pathlib.Path(base) / "manifest.json"
                if not manifest_path.is_file():
                    continue

                try:
                    manifest = json.loads(manifest_path.read_text())
                except ValueError as err:
                    logger.error(
                        "Error parsing manifest.json file at %s: %s", manifest_path, err
                    )
                    continue

        if manifest is None:
            manifest = {
                "references": getattr(module, "REFERENCES", []),
                "requirements": getattr(module, "REQUIREMENTS", []),
            }
        return cls(module, manifest, include_path)

    def __init__(
        self,
        module,
        manifest: Manifest = None,
        include_path: str = None,
    ):
        self.module = module
        self.manifest = manifest or {}
        self.include_path = include_path

    @property
    def references(self):
        return self.manifest.get("references", [])

    @property
    def requirements(self):
        return self.manifest.get("requirements", [])


async def process_requirements(runner, name, requirements):
    async with pip_lock:
        for requirement in requirements:
            if is_installed(requirement):
                continue
            logger.info("Install package: %s for: %s", requirement, name)
            status = await runner.create_job(install_package, requirement)
            if not status:
                logger.error(
                    "Problem with install package: %s for %s", requirement, name
                )


def is_installed(package: str):
    try:
        req = pkg_resources.Requirement.parse(package)
    except ValueError:
        logger.error("Problem with parse: %s", package)
        return False
    try:
        return version(req.project_name) in req
    except PackageNotFoundError:
        return False


def install_package(package: str):
    env = os.environ.copy()
    args = [sys.executable, "-m", "pip", "install", package]
    process = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        # msg = stderr.decode("utf-8").lstrip().strip()
        logger.error("Unable to install package: %s: %s", package)
        return False
    return True
