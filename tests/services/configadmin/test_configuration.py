import pytest
from pytest_mock import MockerFixture

from odss.services.configadmin.services import (
    ConfigurationAdmin,
    SERVICE_PID,
)
from odss.services.configadmin.storages import MemoryStorage

pytestmark = pytest.mark.asyncio


async def test_create_empty_configuration(config_admin: ConfigurationAdmin):
    config = await config_admin.get_configuration("foo.bar")
    properties = config.get_properties()
    assert properties[SERVICE_PID] == "foo.bar"
    assert list(properties.keys()) == [SERVICE_PID]


async def test_get_configuration_from_directory(
    config_storage: MemoryStorage, config_admin: ConfigurationAdmin
):
    directory = config_admin.get_directory()

    await directory.add("foo.bar", {"foo": "bar"}, config_storage)

    config = await config_admin.get_configuration("foo.bar")
    assert config.get_properties() == {SERVICE_PID: "foo.bar", "foo": "bar"}


async def test_get_configuration_from_storage(
    config_storage: MemoryStorage, config_admin: ConfigurationAdmin
):
    config_storage.data["foo.bar"] = {"foo": "bar"}

    config = await config_admin.get_configuration("foo.bar")
    assert config.get_properties() == {SERVICE_PID: "foo.bar", "foo": "bar"}


async def test_notify_service(config_admin: ConfigurationAdmin, mocker: MockerFixture):
    service_mock = mocker.AsyncMock()

    config = await config_admin.get_configuration("mock.pid")

    await config_admin.add_managed_service("mock.pid", service_mock)

    service_mock.updated.assert_called_once_with(
        ({SERVICE_PID: "mock.pid"}),
    )
    service_mock.updated.reset_mock()

    await config.update({"key": "value"})

    service_mock.updated.assert_called_once_with(
        ({SERVICE_PID: "mock.pid", "key": "value"}),
    )

    await config_admin.remove_managed_service("mock.pid", service_mock)


async def test_notify_factory(config_admin: ConfigurationAdmin, mocker: MockerFixture):
    service_mock = mocker.AsyncMock()

    config = await config_admin.create_factory_configuration("factory.pid")

    await config_admin.add_managed_factory("factory.pid", service_mock)

    service_mock.updated.assert_called_once()
    args = service_mock.updated.call_args[0]
    assert args[0].startswith("factory.pid")

    service_mock.updated.reset_mock()

    await config.update({"key": "value"})

    service_mock.updated.assert_called_once()
    args = service_mock.updated.call_args[0]
    assert args[0].startswith("factory.pid")
    assert args[1]["key"] == "value"

    await config_admin.remove_managed_factory("factory.pid", service_mock)


async def test_remove_configuration(
    config_admin: ConfigurationAdmin, mocker: MockerFixture
):
    service_mock = mocker.AsyncMock()

    config = await config_admin.get_configuration("remove.mock.pid")

    await config_admin.add_managed_service("remove.mock.pid", service_mock)

    service_mock.updated.assert_called_once_with({SERVICE_PID: "remove.mock.pid"})
    service_mock.updated.reset_mock()

    await config.remove()

    service_mock.updated.assert_called_once_with(None)

    await config_admin.remove_managed_service("remove.mock.pid", service_mock)


async def test_remove_notify_factory(
    config_admin: ConfigurationAdmin, mocker: MockerFixture
):
    service_mock = mocker.AsyncMock()

    await config_admin.add_managed_factory("factory.pid", service_mock)

    config = await config_admin.create_factory_configuration("factory.pid")

    await config.update({"key": "value"})

    pid = config.get_pid()

    await config.remove()

    service_mock.removed.assert_called_once_with(pid)

    await config_admin.remove_managed_factory("factory.pid", service_mock)


async def test_list_of_configuration(
    config_admin: ConfigurationAdmin, mocker: MockerFixture
):
    config1 = await config_admin.get_configuration("service.pid1")
    config2 = await config_admin.get_configuration("service.pid2")

    configs = config_admin.list_configurations()
    assert len(configs) == 2
    pids = [config1.get_pid(), config2.get_pid()]
    assert configs[0].get_pid() in pids
    assert configs[1].get_pid() in pids


async def test_storage(mocker: MockerFixture):
    admin = ConfigurationAdmin()
    storage = MemoryStorage()
    storage.data = {"service.pid": {SERVICE_PID: "service.pid", "bar": "foo"}}
    service_mock = mocker.AsyncMock()

    await admin.add_storage(storage)

    await admin.add_managed_service("service.pid", service_mock)

    service_mock.updated.assert_called_once_with(
        {SERVICE_PID: "service.pid", "bar": "foo"}
    )


async def test_storage_after_manage_service(mocker: MockerFixture):
    admin = ConfigurationAdmin()
    storage = MemoryStorage()
    storage.data = {"service.pid": {SERVICE_PID: "service.pid", "bar": "foo"}}
    service_mock = mocker.AsyncMock()

    await admin.add_managed_service("service.pid", service_mock)

    await admin.add_storage(storage)

    service_mock.updated.assert_called_once_with(
        {SERVICE_PID: "service.pid", "bar": "foo"}
    )
