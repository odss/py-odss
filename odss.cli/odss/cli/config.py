from dataclasses import dataclass, field
import json
import logging
import os
import typing as t

from importlib.metadata import entry_points


ENTRY_POINT_GROUP = "odss.bundle"


DEFAULT_PATH = (
    "/etc/default",
    "/etc",
    "/usr/local/etc",
    "~/.local/odss",
    "~",
    ".",
)
DEFAULT_FILE = "odss.json"


@dataclass
class Config:
    debug: bool = False
    properties: dict[str, t.Any] = field(default_factory=dict)
    bundles: list[str] = field(default_factory=list)
    entries: dict[str, str] = field(default_factory=dict)

    def extend(self, payload: dict[str, str]) -> None:
        self.properties.update(payload.get("properties", {}))
        self.bundles.extend(payload.get("bundles", []))

    def normalize(self) -> None:
        self.bundles = [
            self.entries.get(bundle, bundle) for bundle in set(self.bundles)
        ]


def load_config(include_entry_points: bool = False, debug: bool = False) -> Config:
    entries = {e.name: e.value for e in entry_points(group=ENTRY_POINT_GROUP)}
    config = Config(entries=entries)
    for file_path in find_default_configs():
        if file_path is not None:
            logging.info("Load config: %s", file_path)
            with open(file_path, "r") as fh:
                config.extend(json.load(fh))
    if include_entry_points:
        bundles = find_bundles_in_entry_points()
        config.bundles.extend(bundles)
    return config


def find_bundles_in_entry_points():
    entries = entry_points(group=ENTRY_POINT_GROUP)
    return [entry.value for entry in entries]


def find_default_configs() -> t.Iterable[str]:
    for dir_path in DEFAULT_PATH:
        dir_path = os.path.expanduser(dir_path)
        full_name = os.path.join(dir_path, DEFAULT_FILE)
        if os.path.exists(full_name):
            yield full_name
