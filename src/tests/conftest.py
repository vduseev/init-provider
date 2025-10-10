import asyncio
import sys

import pytest

from init_provider import BaseProvider, requires
from init_provider._internal._metaclass import ProviderMetaclass


class UsersDatabase(BaseProvider):
    _init_counter = 0
    _users: dict[int, str] = {}

    def provider_init(self):
        self._users = self.fetch()
        self._init_counter += 1

    def get(self, id: int) -> str:
        return self._users[id]

    def add(self, id: int, name: str) -> None:
        self._users[id] = name

    @classmethod
    def fetch(cls) -> dict[int, str]:
        return {1: "john", 2: "jane"}


@requires(UsersDatabase)
class UsersCacheProvider(BaseProvider):
    _init_counter = 0
    _access_counter = 0
    _access_limit = 2
    _users: dict[int, str]

    def provider_init(self):
        self._users = {}
        self._init_counter += 1

    def get(self, id: int) -> str:
        self._access_counter += 1
        if id not in self._users:
            self._users[id] = UsersDatabase.get(id)
        elif self._access_counter > self._access_limit:
            self._users[id] = UsersDatabase.get(id)
        return self._users[id]


class UsersService(BaseProvider):
    _init_counter = 0

    def provider_init(self):
        self._init_counter += 1

    async def fetch(self) -> str:
        await asyncio.sleep(0)  # Yield control to event loop
        return "async_data"


@pytest.fixture
def clean_sys_modules():
    """Remove any test providers from sys.modules after each test."""
    yield
    # Clean up any dynamically created provider classes
    to_remove = []
    for module_name in sys.modules:
        if module_name.startswith("test_") or "conftest" in module_name:
            to_remove.append(module_name)

    for module_name in to_remove:
        if module_name in sys.modules:
            del sys.modules[module_name]

    # Reset metaclass state
    ProviderMetaclass.__provider_setup_done__ = False
    ProviderMetaclass.__provider_setup_hook__ = None
    ProviderMetaclass.__provider_dispose_hook__ = None
    ProviderMetaclass.__providers__ = []
