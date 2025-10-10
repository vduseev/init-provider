import pytest

from init_provider import BaseProvider, requires
from init_provider.exceptions import ProviderDefinitionError


def test_requires_sets_dependency_attribute(clean_sys_modules):
    class ProviderSimple(BaseProvider):
        data: str

        def provider_init(self):
            self.data = "simple_data"

    @requires(ProviderSimple)
    class TestProvider(BaseProvider):
        def get_data(self):
            return ProviderSimple.data

    # Check that the dependency was correctly set
    assert TestProvider.__provider_dependencies__ == {ProviderSimple}

    # Test with multiple dependencies
    class DummyProvider(BaseProvider):
        data: str

        def provider_init(self):
            self.data = "dummy_data"

    @requires(TestProvider, ProviderSimple, DummyProvider)
    class MultiDepProvider(BaseProvider):
        def get_data(self):
            return f"{TestProvider.get_data()}-{DummyProvider.data}"

    # Check that both dependencies were set
    assert MultiDepProvider.__provider_dependencies__ == {
        ProviderSimple,
        DummyProvider,
        TestProvider,
    }


def test_requires_raises_if_dependency_not_subclass_of_baseprovider(clean_sys_modules):
    class NotProvider(object):
        pass

    with pytest.raises(
        ProviderDefinitionError,
        match="Cannot use NotProvider as a dependency because it is not a subclass of BaseProvider",
    ):
        @requires(NotProvider)  # type: ignore[arg-type]
        class TestProvider(BaseProvider):
            pass


def test_requires_raises_if_decorated_class_not_baseprovider(clean_sys_modules):
    class TestProvider(BaseProvider):
        pass

    with pytest.raises(
        ProviderDefinitionError,
        match="Cannot use @requires on NotProvider because it is not a subclass of BaseProvider",
    ):
        @requires(TestProvider)  # type: ignore[arg-type]
        class NotProvider:
            pass
