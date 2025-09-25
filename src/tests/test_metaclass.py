import inspect

import pytest

from init_provider import BaseProvider, init
from init_provider.provider import ProviderMetaclass
from init_provider.exceptions import ProviderDefinitionError


def test_basic(clean_sys_modules):
    class TestProvider(BaseProvider):
        guarded_attr: str
        _init_counter = 0

        def __init__(self):
            self.guarded_attr = "A"
            self._init_counter += 1

        @init
        def get_guarded_attr(self) -> str:
            return self.guarded_attr

    # Metaclass
    assert TestProvider.__class__ is ProviderMetaclass
    assert TestProvider.__bases__ == (BaseProvider,)
    assert TestProvider.__provider_initialized__ is False
    assert TestProvider.__provider_dependencies__ == set()
    assert TestProvider.__provider_init__ is not None

    # Guards
    assert not inspect.isfunction(TestProvider.get_guarded_attr)
    assert inspect.ismethod(TestProvider.get_guarded_attr)
    assert "guarded_attr" in TestProvider.__provider_guarded_attrs__


def test_plain_function_disallowed(clean_sys_modules):
    with pytest.raises(
        ProviderDefinitionError,
        match="must be decorated with @classmethod, @staticmethod, or @init",
    ):

        class PlainFunctionProvider(BaseProvider):
            def __init__(self):
                pass

            def helper_function(self):  # This should trigger the error
                return "helper"


def test_init_not_allowed_on_init(clean_sys_modules):
    with pytest.raises(
        ProviderDefinitionError,
        match="is a reserved method and cannot be decorated with @init",
    ):

        class InitOnInitializeProvider(BaseProvider):
            @init
            def __init__(self):
                pass
