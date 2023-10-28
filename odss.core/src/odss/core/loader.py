import asyncio
import contextlib
import dataclasses as dts
import importlib
import importlib.util
import json
import logging
import sys
from pathlib import Path

from .loop import create_job

logger = logging.getLogger(__name__)

pip_lock = asyncio.Lock()
import_lock = asyncio.Lock()


@dts.dataclass(frozen=True)
class Manifest:
    requirements: list[str]
    references: list[str]

    @staticmethod
    def empty():
        return Manifest(requirements=[], references=[])


async def load_bundle(name: str, path: str | None = None) -> "Integration":
    async with import_lock:
        manifest = await create_job(find_manifest, name, path)
    async with pip_lock:
        await process_requirements(name, manifest.requirements)

    async with import_lock:
        integration = await create_job(Integration.load_sync, name, path)
    integration.manifest = manifest
    return integration


def import_module(name: str, path: str | None = None):
    logger.debug("Import module: %s with path: %s", name, path)
    try:
        with sys_path(path):
            module = importlib.import_module(name)
            return module
    except ImportError as ex:
        raise RuntimeError("Error installing bundle '{0}': {1}".format(name, ex))


def find_manifest(name: str, path: str | None = None):
    with sys_path(path):
        try:
            spec = importlib.util.find_spec(name)
        except ModuleNotFoundError:
            spec = None
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
    for key, module in sorted(sys.modules.items()):
        if key.startswith(name) and hasattr(module, "__file__"):
            try:
                del sys.modules[key]
            except KeyError:
                pass
            try:
                # Clear parent reference
                parent, basename = key.rsplit(".", 1)
                if parent:
                    delattr(sys.modules[parent], basename)
            except (KeyError, AttributeError, ValueError):
                pass


@contextlib.contextmanager
def sys_path(path: str | None):
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
    manifest: Manifest

    @classmethod
    def load_sync(cls, name: str, include_path: str | None = None):
        module = import_module(name, include_path)
        return cls(module, Manifest.empty(), include_path)

    def __init__(
        self,
        module,
        manifest: Manifest| None = None,
        include_path: str | None = None,
    ):
        self.module = module
        self.manifest = manifest or Manifest.empty()
        self.include_path = include_path

    @property
    def references(self) -> list[str]:
        return self.manifest.references

    @property
    def requirements(self) -> list[str]:
        return self.manifest.requirements


async def process_requirements(name, requirements):
    for requirement in requirements:
        if is_installed(requirement):
            continue
        logger.info("Install package: %s for: %s", requirement, name)
        status = await install_package(requirement)
        if not status:
            logger.error("Problem with install package: %s for %s", requirement, name)


def is_installed(package: str):
    # @todo fix
    return True


async def install_package(package: str):
    # env = os.environ.copy()
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
