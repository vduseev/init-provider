import pytest

from init_provider import BaseProvider
from init_provider.exceptions import (
    ProviderDefinitionError,
)


def test_del_args(clean_sys_modules):
    with pytest.raises(
        ProviderDefinitionError,
        match="Cannot use __del__ with arguments",
    ):

        class ProviderWithArgs(BaseProvider):
            def __del__(self, arg1: int, arg2: int):  # type: ignore
                print(arg1 + arg2)
