import pytest

from odss.services.configadmin.services import ConfigurationAdmin
from odss.services.configadmin.storages import MemoryStorage


@pytest.fixture()
def config_storage():
    return MemoryStorage()


@pytest.fixture()
@pytest.mark.asyncio
async def config_admin(config_storage):
    admin = ConfigurationAdmin()
    await admin.add_storage(config_storage)
    yield admin
    await admin.remove_storage(config_storage)


@pytest.fixture()
def config_directory(config_admin):
    yield config_admin.get_directory()
