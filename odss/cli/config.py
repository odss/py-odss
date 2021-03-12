import os
import json
import logging
import typing as t


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

    def load(self, file_path: str = None) -> None:
        if file_path is not None:
            logging.info("Load config: %s", file_path)
            with open(file_path, "r") as fh:
                self.extend(json.load(fh))
        else:
            for file_path in self._find_default_configs():
                self.load(file_path)

    def extend(self, payload: t.Dict[str, str]) -> None:
        self.bundles.extend(payload.get("bundles", []))
        self.properties.update(payload.get("properties", {}))

    def normalize(self) -> None:
        self.bundles = list(remove_duplicates(self.bundles))

    def _find_default_configs(self) -> t.Iterable[str]:
        for dir_path in self.DEFAULT_PATH:
            dir_path = os.path.expanduser(dir_path)
            full_name = os.path.join(dir_path, self.DEFAULT_FILE)
            if os.path.exists(full_name):
                yield full_name


def remove_duplicates(items):
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
            yield item
