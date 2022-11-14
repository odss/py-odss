import os
import json
import shutil
import argparse
from pathlib import Path
from dataclasses import dataclass, field

from build import ProjectBuilder
from setuptools.config.setupcfg import read_configuration
from invoke import task

DEV_ROOT = Path(__file__).parent
ROOT = DEV_ROOT.parent

SETUP_FILE = "setup.cfg"


@dataclass
class Entry:
    name: str
    match: str
    deps: list[str]
    commands: list[str]
    is_dev: bool = False
    is_test: bool = False


@dataclass
class Config:
    entries: list[Entry]
    manifest: str
    devs: list[str]

    @classmethod
    def create(cls):
        with open(DEV_ROOT / "config.json") as f:
            config = json.load(f)
        with open(DEV_ROOT / "tpls" / "manifest.txt") as f:
            manifest = f.read()

        entries = [Entry(**entry) for entry in config["entries"]]
        return Config(
            entries=entries,
            manifest=manifest,
            devs=config["devs"],
        )


config = Config.create()


@dataclass
class Pkg:
    path: Path
    config: dict
    setup: str
    entries: list[Entry] = field(default_factory=list)

    @property
    def name(self):
        return self.config["metadata"]["name"]

    def is_empty(self):
        return not self.entries

    def has_tests(self):
        for entry in self.entries:
            if entry.is_test:
                return True
        return False

    def has_typing(self):
        for entry in self.entries:
            if entry.name == "typing":
                return True
        return False


class IBuilder:
    def build(self, path: Path, force: bool):
        pass


@dataclass
class Requirements(IBuilder):
    def build(self, pkg: Pkg, force: bool = False):
        dir_path = pkg.path / "requirements"
        if force and dir_path.exists():
            shutil.rmtree(dir_path)

        if not dir_path.exists():
            dir_path.mkdir()

        names = []
        for entry in pkg.entries:
            self.build_entry(entry, dir_path)
            if entry.is_dev:
                names.append(self.file_name(entry))

        dev = [f"-r {name}" for name in names]
        dev.extend(["", "ipdb==0.10.3", "pre-commit==2.17.0"])
        self.build_entry(
            Entry("dev", "", dev, [], []),
            dir_path,
        )

    def build_entry(self, entry: Entry, path: Path):
        file_path = path / self.file_name(entry)
        if not file_path.exists():
            file_path.write_text("\n".join(entry.deps))

    def file_name(self, entry: Entry):
        return f"{entry.name}.txt"


@dataclass
class Tox(IBuilder):
    def build(self, pkg: Pkg, force: bool = False):
        file_path = pkg.path / "tox.ini"
        if force and file_path.exists():
            file_path.unlink()

        if file_path.exists():
            return

        parts = [
            "[tox]",
            "minversion = 3.10.0",
            "envlist = ",
        ]
        envs = []
        sections = []
        for entry in pkg.entries:
            envs.append("    " + entry.name)
            section_name = "[testenv]" if entry.is_test else f"[testenv:{entry.name}]"
            section = [
                "",
                section_name,
                f"deps = -r requirements/{entry.name}.txt",
                "changedir = {toxinidir}",
                "commands = ",
            ]
            cmds = ["    " + command for command in entry.commands]
            sections.extend(section + cmds)
        content = "\n".join(parts + envs + sections)
        file_path.write_text(content)


class Manifest:
    def build(self, pkg: Pkg, force: bool = False):
        if not pkg.is_empty():
            file_path = pkg.path / "MANIFEST.in"
            if force and file_path.exists():
                file_path.unlink()

            if file_path.exists():
                return

            file_path.write_text(config.manifest)


def find_pkg(path: Path):
    for entry in os.scandir(path):
        if entry.is_dir() and not entry.name.startswith("."):
            setup_path = Path(entry.path) / SETUP_FILE
            if setup_path.exists():
                config = read_configuration(setup_path)
                yield Pkg(setup_path.parent, config, setup_path.read_text())


def sort_pkgs(pkgs: list[Pkg]) -> list[Pkg]:
    pkgs = list(pkgs)
    to_sort = []
    names = []
    for pkg in pkgs:
        deps = pkg.config.get("options", {}).get("install_requires", [])
        names.append(pkg.config["metadata"]["name"])
        to_sort.append([dep.split("==")[0].strip() for dep in deps])

    moves = []
    for i, deps in enumerate(to_sort):
        m = 0
        for dep in deps:
            try:
                m = max(m, names.index(dep) + 1)
            except ValueError:
                pass
        moves.append((m, pkgs[i]))

    return [pkg for _, pkg in sorted(moves, key=lambda i: i[0])]


def load_pkg(root: Path) -> list[Pkg]:
    for pkg in sort_pkgs(find_pkg(root)):
        for entry in config.entries:
            if entry.match in pkg.setup:
                pkg.entries.append(entry)
        yield pkg


def update_pkg(pkgs: list[Pkg], force: bool):
    builders = [Manifest(), Requirements(), Tox()]
    for pkg in pkgs:
        for builder in builders:
            builder.build(pkg, force)


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="odss dev")

    group = parser.add_argument_group("options")
    group.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force",
    )
    return parser.parse_args()


@task
def update(c, force=False):
    pkgs = load_pkg(ROOT)
    update_pkg(pkgs, force)


@task
def local_install(c):
    names = " ".join(f"-e {pkg.path}" for pkg in load_pkg(ROOT))
    c.run(f"pip install {names}")


@task
def clean(c):
    print("Cleaning")
    names = [
        "__pycache__",
        "*.py[co]",
        "cache",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        "dist",
    ]
    for name in names:
        c.run(f"rm -rf `find {ROOT} -name {name}`")


@task(clean)
def build(c):
    print("Building")
    for pkg in load_pkg(ROOT):
        # c.run(f'python -m build -n {pkg.path}')
        builder = ProjectBuilder(pkg.path)
        for distribution in ['sdist', 'wheel']:
            builder.build(distribution, pkg.path / "dist")


@task(build)
def devpi_publish(c):
    print("Publish")
    for pkg in load_pkg(ROOT):
        c.run(f"devpi upload --no-vcs --from-dir {pkg.path}")


@task
def devpi_clean(c):
    for pkg in load_pkg(ROOT):
        c.run(f"devpi remove -y {pkg.name}")


@task
def devpi_test(c):
    for pkg in load_pkg(ROOT):
        c.run(f"""devpi test -s . --tox-args="-p" {pkg.name} """)


# if __name__ == "__main__":
#     main()
