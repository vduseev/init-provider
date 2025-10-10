import inspect

import pytest

from init_provider import BaseProvider
from init_provider.provider import ProviderMetaclass
from init_provider.exceptions import ProviderDefinitionError


def test_basic(clean_sys_modules):
    class TestProvider(BaseProvider):
        guarded_attr: str
        _init_counter = 0

        def provider_init(self):
            self.guarded_attr = "A"
            self._init_counter += 1

        def get_guarded_attr(self) -> str:
            return self.guarded_attr

    # Metaclass
    assert TestProvider.__class__ is ProviderMetaclass
    assert TestProvider.__bases__ == (BaseProvider,)
    assert TestProvider.__provider_initialized__ is False
    assert TestProvider.__provider_dependencies__ == set()
    assert TestProvider.provider_init is not None

    # Guards
    assert not inspect.isfunction(TestProvider.get_guarded_attr)
    assert inspect.ismethod(TestProvider.get_guarded_attr)
    assert "guarded_attr" in TestProvider.__provider_guarded_attrs__
