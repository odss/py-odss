import importlib
import sys
import threading


def load_bundle(name: str, path: str = None):
    print("load_bundle", name, path)
    return load_package(name, path)


def unload_bundle(name):
    try:
        del sys.modules[name]
    except KeyError:
        pass


def load_package(name: str, path=None):
    print("load_package", name, path, threading.current_thread().name)
    try:
        if path:
            sys.path.insert(0, path)
        return importlib.import_module(name)
    except Exception as ex:
        raise RuntimeError("Error installing bundle '{0}': {1}".format(name, ex))
    finally:
        if path:
            sys.path.remove(path)
