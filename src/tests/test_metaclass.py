import inspect

from init_provider import BaseProvider, init
from init_provider.provider import ProviderMetaclass


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
    assert TestProvider.__provider_created__ is False
    assert TestProvider.__provider_dependencies__ == set()
    assert TestProvider.__provider_init__ is not None  # type: ignore[unresolved-attribute]

    # Guards
    assert not inspect.isfunction(TestProvider.get_guarded_attr)
    assert inspect.ismethod(TestProvider.get_guarded_attr)
    assert "guarded_attr" in TestProvider.__provider_guarded_attrs__
    assert "_init_counter" not in TestProvider.__provider_guarded_attrs__
