import pytest

from init_provider import BaseProvider, setup
from init_provider.provider import ProviderMetaclass
from init_provider.exceptions import ProviderDefinitionError


def test_setup_runs_once(clean_sys_modules):
    setup_counter = 0

    @setup
    def test_setup():
        nonlocal setup_counter
        setup_counter += 1
        print("LALAL")

    assert ProviderMetaclass.__provider_setup_hook__ is test_setup

    class Provider1(BaseProvider):
        _sdata: str
        _init_counter = 0

        def provider_init(self):
            self._data = "data1"
            self._init_counter += 1

        def set_data(self, data: str):
            self._data = data

    class Provider2(BaseProvider):
        data: str
        _init_counter = 0

        def provider_init(self):
            self.data = "data2"
            self._init_counter += 1

    # Access first provider - should trigger setup
    Provider1.set_data("data1-modified")
    assert Provider1._init_counter == 1
    assert Provider2._init_counter == 0
    assert setup_counter == 1

    # Access second provider - setup should not run again
    assert Provider2.data == "data2"
    assert Provider1._init_counter == 1
    assert Provider2._init_counter == 1
    assert setup_counter == 1


def test_setup_raises_if_expects_arguments(clean_sys_modules):
    with pytest.raises(
        ProviderDefinitionError,
        match="is a function that expects arguments and cannot be used as a setup function",
    ):

        @setup  # type: ignore[arg-type]
        def test_setup(arg: str):
            pass
