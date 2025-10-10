from __future__ import annotations

import atexit
import logging
from abc import ABCMeta
from types import FunctionType
from typing import Any, Callable, TYPE_CHECKING, cast

from ..exceptions import (
    SetupError,
    DisposeError,
    AttributeNotInitialized,
    ProviderDefinitionError,
)
from ._utils import (
    _initialize_provider_chain,
    _sort_providers,
    _wrap_guarded_method,
)

if TYPE_CHECKING:
    from ..provider import BaseProvider


logger = logging.getLogger("init_provider")
__all__ = ["ProviderMetaclass"]


class ProviderMetaclass(ABCMeta):
    __providers__: list[type] = []
    __provider_setup_done__: bool = False
    __provider_setup_hook__: Callable | None = None
    __provider_dispose_hook__: Callable | None = None

    def __new__(
        mcls: type,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        **kwds: Any,
    ) -> type:
        annotations: dict[str, Any] = namespace.get("__annotations__", {})
        new_ns: dict[str, Any] = {}

        for attr, value in namespace.items():
            if attr in ("provider_init", "provider_dispose"):
                new_ns[attr] = classmethod(value)
            elif (
                isinstance(value, FunctionType)
                and not (attr.startswith("__") and attr.endswith("__"))
            ):
                guarded_func = _wrap_guarded_method(value)
                new_ns[attr] = classmethod(guarded_func)
            else:
                # Class methods, static methods, attributes with values are
                # all passed as is.
                new_ns[attr] = value

        # Class variables with type annotations but without values (similar
        # to dataclass fields) become guarded attributes and will trigger
        # provider initialization, when accessed.
        guarded_attrs = {k for k in annotations.keys() if k not in new_ns}
        new_ns["__provider_guarded_attrs__"] = guarded_attrs

        cls: type = ABCMeta.__new__(mcls, name, bases, new_ns, **kwds)
        providers: list[type] = type.__getattribute__(mcls, "__providers__")
        if cls.__name__ != "BaseProvider":
            providers.append(cls)
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
    def _ensure_setup_hook_executed() -> None:
        # Run the one-time setup hook if it is defined. This is only done once
        # per runtime. It is designed to configure logging, disable warnings,
        # or monkey-patch things before the rest of the application starts.
        if (
            not ProviderMetaclass.__provider_setup_done__
            and ProviderMetaclass.__provider_setup_hook__ is not None
        ):
            try:
                result = ProviderMetaclass.__provider_setup_hook__()
                ProviderMetaclass.__provider_setup_done__ = True
                if result is None:
                    summary = "Setup hook executed."
                else:
                    summary = f"Setup hook executed with result: {result}"
                logger.info(summary)
            except Exception as e:
                raise SetupError(e) from e
            
    @staticmethod
    def _ensure_dispose_hook_executed() -> None:
        # Call the provider_dispose() method of each provider in the reverse
        # order of their initialization.
        order = _sort_providers(ProviderMetaclass.__providers__)
        dispose_order: list[tuple[str, Callable]] = []
        for provider in reversed(order):
            if hasattr(provider, "provider_dispose"):
                func = type.__getattribute__(provider, "provider_dispose")
                if callable(func):
                    dispose_order.append((provider.__name__, func))

        names = [t[0] for t in dispose_order]
        logger.debug(f"Provider dispose call order: {names}")

        for name, func in dispose_order:
            try:
                result = func()
            except Exception as e:
                raise DisposeError(e) from e
            if result is None:
                summary = f"Dispose hook for {name} was executed."
            else:
                summary = f"Dispose hook for {name} was executed with result: {result}"
            logger.info(summary)

        # Trigger an explicit @dispose hook, if it is defined.
        if ProviderMetaclass.__provider_dispose_hook__ is not None:
            try:
                result = ProviderMetaclass.__provider_dispose_hook__()
            except Exception as e:
                raise DisposeError(e) from e
            if result is None:
                summary = "Dispose hook executed."
            else:
                summary = f"Dispose hook executed with result: {result}"
            logger.info(summary)


atexit.register(ProviderMetaclass._ensure_dispose_hook_executed)
