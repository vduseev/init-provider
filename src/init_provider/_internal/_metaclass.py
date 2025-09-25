from __future__ import annotations

import logging
from abc import ABCMeta
from types import FunctionType
from typing import Any, Callable, TYPE_CHECKING, cast

from ..exceptions import (
    SetupError,
    AttributeNotInitialized,
    ProviderDefinitionError,
    InitCalledDirectly,
)
from ._utils import _initialize_provider_chain

if TYPE_CHECKING:
    from ..provider import BaseProvider


logger = logging.getLogger("init_provider")
__all__ = ["ProviderMetaclass"]


class ProviderMetaclass(ABCMeta):
    __provider_setup_done__: bool = False
    __provider_setup_hook__: Callable | None = None

    def __new__(
        mcls: type,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        **kwds: Any,
    ) -> type:
        # All methods other than __init__ must be decorated with @classmethod
        # or @staticmethod.
        for attr, value in namespace.items():
            if (
                attr != "__init__"
                and isinstance(value, FunctionType)
                and not (attr.startswith("__") and attr.endswith("__"))
            ):
                raise ProviderDefinitionError(
                    f"Method {name}.{attr} must be decorated with "
                    "@classmethod, @staticmethod, or @init to comply with "
                    "the provider protocol"
                )

        annotations: dict[str, Any] = namespace.get("__annotations__", {})
        new_ns: dict[str, Any] = {}

        def _init_plug(*args: Any, **kwargs: Any) -> None:
            """Prevent users from calling __init__() directly.

            The __init__() method is only meant to be called by the provider
            initialization process.
            """
            raise InitCalledDirectly(name)

        _init_plug.__name__ = "__init__"

        for attr, value in namespace.items():
            if attr == "__init__":
                # The mandatory __init__() method is hijacked and hidden
                # from the user.
                value.__name__ = "__provider_init__"
                new_ns["__provider_init__"] = classmethod(value)
                new_ns["__init__"] = classmethod(_init_plug)
            else:
                # Class methods, static methods, attributes with values are
                # all passed as is.
                new_ns[attr] = value

        guarded_attrs = {k for k in annotations.keys() if k not in new_ns}
        new_ns["__provider_guarded_attrs__"] = guarded_attrs

        cls: type = ABCMeta.__new__(mcls, name, bases, new_ns, **kwds)
        return cls

    def __getattribute__(cls, name: str) -> Any:
        try:
            guarded_attrs: set[str] = type.__getattribute__(
                cls, "__provider_guarded_attrs__"
            )
        except AttributeError:
            pass
        else:
            if name in guarded_attrs:
                is_initialized: bool = type.__getattribute__(
                    cls, "__provider_initialized__"
                )
                if not is_initialized:
                    provider_cls = cast("type[BaseProvider]", cls)
                    _initialize_provider_chain(provider_cls, requested_for=name)
                if name not in cls.__dict__:
                    raise AttributeNotInitialized(cls.__name__, name)
        result = type.__getattribute__(cls, name)
        return result

    def __setattr__(cls, name: str, value: Any) -> None:
        try:
            guarded_attrs: set[str] = type.__getattribute__(
                cls, "__provider_guarded_attrs__"
            )
        except AttributeError:
            pass
        else:
            if name in guarded_attrs:
                guarded_attrs.remove(name)
        type.__setattr__(cls, name, value)

    @staticmethod
    def _ensure_setup_configured() -> None:
        # Run the one-time setup hook if it is defined. This is only done once
        # per runtime. It is designed to configure logging, disable warnings,
        # or monkey-patch things before the rest of the application starts.
        if (
            not ProviderMetaclass.__provider_setup_done__
            and ProviderMetaclass.__provider_setup_hook__ is not None
        ):
            try:
                ProviderMetaclass.__provider_setup_hook__()
                ProviderMetaclass.__provider_setup_done__ = True
                logger.info("Setup hook executed successfully.")
            except Exception as e:
                raise SetupError(e) from e
