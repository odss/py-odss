import pytest

from odss.services.configadmin.services import (
    ConfigurationDirectory,
    SERVICE_PID,
)
from odss.services.configadmin.storages import MemoryStorage


pytestmark = pytest.mark.asyncio


async def test_create_configuration(
    config_storage: MemoryStorage, config_directory: ConfigurationDirectory
):
    configuration = await config_directory.add(
        "foo.bar", {"foo": "bar"}, config_storage
    )

    assert configuration.get_pid() == "foo.bar"
    assert configuration.get_properties() == {SERVICE_PID: "foo.bar", "foo": "bar"}
    assert config_storage.data == {"foo.bar": {SERVICE_PID: "foo.bar", "foo": "bar"}}
    assert config_directory.exists("foo.bar")


async def test_update_configuration_by_directory(
    config_storage: MemoryStorage, config_directory: ConfigurationDirectory
):
    configuration = await config_directory.add(
        "foo.bar", {"foo": "bar"}, config_storage
    )

    await config_directory.update("foo.bar", {"bar": "foo"}, replace=True)
    assert configuration.get_properties() == {SERVICE_PID: "foo.bar", "bar": "foo"}
    assert config_storage.data == {"foo.bar": {SERVICE_PID: "foo.bar", "bar": "foo"}}


async def test_remove_configuration_by_directory(
    config_storage: MemoryStorage, config_directory: ConfigurationDirectory
):
    configuration = await config_directory.add(
        "foo.bar", {"foo": "bar"}, config_storage
    )

    await config_directory.remove("foo.bar")
    with pytest.raises(ValueError):
        assert configuration.get_properties()

    assert config_storage.data == {}


async def test_update_configuration(
    config_storage: MemoryStorage, config_directory: ConfigurationDirectory
):

    configuration = await config_directory.add(
        "foo.bar", {"foo": "bar"}, config_storage
    )

    assert await configuration.update({"foo": "bar"}) is False

    assert await configuration.update({"bar": "foo"}) is True

    assert config_storage.data == {
        "foo.bar": {SERVICE_PID: "foo.bar", "foo": "bar", "bar": "foo"}
    }

    assert await configuration.update({"bar": "foo"}, replace=True) is True

    assert config_storage.data == {"foo.bar": {SERVICE_PID: "foo.bar", "bar": "foo"}}


async def test_remove_configuration(
    config_storage: MemoryStorage, config_directory: ConfigurationDirectory
):
    configuration = await config_directory.add(
        "foo.bar", {"foo": "bar"}, config_storage
    )

    await configuration.remove()

    assert config_storage.data == {}


async def test_get_list_of_configuration(
    config_storage: MemoryStorage, config_directory: ConfigurationDirectory
):
    await config_directory.add("foo.bar", {"foo": "bar"}, config_storage)
    await config_directory.add("x.y.z", {"x": "a", "y": "b", "z": "c"}, config_storage)

    configs = config_directory.list_configurations()
    assert len(configs) == 2

    configs = config_directory.list_configurations({"foo": "bar"})
    assert len(configs) == 1
    assert configs[0].get_properties()["foo"] == "bar"

    configs = config_directory.list_configurations({SERVICE_PID: "x.y.z"})
    assert len(configs) == 1

    props = configs[0].get_properties()
    assert props["x"] == "a"
    assert props["y"] == "b"
    assert props["z"] == "c"

    configs = config_directory.list_configurations({"a": "b"})
    assert len(configs) == 0


async def test_get_list_of_configuration(
    config_storage: MemoryStorage, config_directory: ConfigurationDirectory
):
    await config_directory.add("foo.bar", {"foo": "bar"}, config_storage)
    await config_directory.add("x.y.z", {"x": "a", "y": "b", "z": "c"}, config_storage)

    configs = config_directory.list_configurations()
    assert len(configs) == 2

    configs = config_directory.list_configurations({"foo": "bar"})
    assert len(configs) == 1
    assert configs[0].get_properties()["foo"] == "bar"

    configs = config_directory.list_configurations({SERVICE_PID: "x.y.z"})
    assert len(configs) == 1

    props = configs[0].get_properties()
    assert props["x"] == "a"
    assert props["y"] == "b"
    assert props["z"] == "c"

    configs = config_directory.list_configurations({"a": "b"})
    assert len(configs) == 0


async def test_get_factories(
    config_storage: MemoryStorage, config_directory: ConfigurationDirectory
):
    await config_directory.add(
        "foo.bar", {"foo": "bar"}, config_storage, "factory.foo.bar"
    )
    await config_directory.add(
        "x.y.z", {"x": "a", "y": "b", "z": "c"}, config_storage, "factory.foo.bar"
    )

    configs = config_directory.get_factory_configurations("factory.foo.bar")
    assert len(configs) == 2

    configs = config_directory.get_factory_configurations("foo.bar")
    assert len(configs) == 0

    configs = config_directory.get_factory_configurations("x.y.z")
    assert len(configs) == 0

    await config_directory.remove("foo.bar")
    await config_directory.remove("x.y.z")

    configs = config_directory.get_factory_configurations("factory.foo.bar")
    assert len(configs) == 0
