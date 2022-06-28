import asyncio
import contextlib
import importlib
import json
import logging
import os
import subprocess
import sys
import dataclasses as dts
import typing as t
import importlib.util
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version

import pkg_resources

logger = logging.getLogger(__name__)

pip_lock = asyncio.Lock()


@dts.dataclass(frozen=True)
class Manifest:
    requirements: t.List[str]
    references: t.List[str]


async def load_bundle(runner, name: str, path: str = None) -> "Integration":
    manifest = await runner.create_job(find_manifest, name, path)
    if manifest:
        await process_requirements(runner, name, manifest.requirements)

    integration = await runner.create_job(Integration.load_sync, name, path)
    integration.manifest = manifest
    return integration


def import_module(name: str, path: str = None):
    logger.debug("Import module: %s with path: %s", name, path)
    try:
        with sys_path(path):
            module = importlib.import_module(name)
            return module
    except ImportError as ex:
        raise RuntimeError("Error installing bundle '{0}': {1}".format(name, ex))


def find_manifest(name: str, path: str = None):
    with sys_path(path):
        spec = importlib.util.find_spec(name)

    manifest_data = {}
    if spec and spec.origin:
        dir_path = Path(spec.origin).parent
        manifest_path = Path(dir_path) / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest_data = json.loads(manifest_path.read_text())
            except ValueError as err:
                logger.error(
                    "Error parsing manifest.json file at %s: %s", manifest_path, err
                )
    return Manifest(
        manifest_data.get("requirements", []),
        manifest_data.get("references", []),
    )


def unload_bundle(name):
    try:
        del sys.modules[name]
    except KeyError:
        pass

    try:
        # Clear parent reference
        parent, basename = name.rsplit(".", 1)
        if parent:
            delattr(sys.modules[parent], basename)
    except (KeyError, AttributeError, ValueError):
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


def is_package(module) -> bool:
    return hasattr(module, "__path__")


class Integration:
    @classmethod
    def load_sync(cls, name: str, include_path: str = None):
        module = import_module(name, include_path)
        return cls(module, None, include_path)

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
        return self.manifest.references

    @property
    def requirements(self):
        return self.manifest.requirements


async def process_requirements(runner, name, requirements):
    async with pip_lock:
        for requirement in requirements:
            if is_installed(requirement):
                continue
            logger.info("Install package: %s for: %s", requirement, name)
            status = await install_package(requirement)
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


async def install_package(package: str):
    env = os.environ.copy()
    args = []
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pip",
        "install",
        package,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        msg = stderr.decode("utf-8").lstrip().strip()
        logger.error("Unable to install package: %s: %s", package, msg)
        return False
    return True
