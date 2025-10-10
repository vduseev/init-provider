import asyncio
import inspect
import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from functools import wraps
from typing import (
    TypeVar,
    ParamSpec,
    Concatenate,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from ..provider import BaseProvider

from ..exceptions import (
    CircularDependency,
    DependencyChainMismatch,
    InitError,
    SelfDependency,
)


_P = ParamSpec("_P")
_R = TypeVar("_R")
_PT = TypeVar("_PT", bound="BaseProvider")


logger = logging.getLogger("init_provider")
_sync_init_lock = threading.RLock()
"""Guarantee that two threads cannot call provider_init() of the same
provider at the same time.
"""

__all__ = [
    "_sort_providers",
    "_initialize_provider_chain",
    "_wrap_guarded_method",
]


def _event_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def _raise_on_circular_dependencies(
    cls: type[_PT],
    visited: set[type["BaseProvider"]] | None = None,
    recursion_stack: set[type["BaseProvider"]] | None = None,
) -> None:
    if visited is None:
        visited = set()
    if recursion_stack is None:
        recursion_stack = set()

    if cls in recursion_stack:
        raise CircularDependency(
            provider=cls.__name__,
            recursion_stack=[d.__name__ for d in recursion_stack],
        )

    if cls in visited:
        return

    visited.add(cls)
    recursion_stack.add(cls)

    for dep in cls.__provider_dependencies__:
        _raise_on_circular_dependencies(dep, visited, recursion_stack)

    recursion_stack.remove(cls)


def _get_all_dependencies(cls: type[_PT]) -> set[type["BaseProvider"]]:
    deps = set(cls.__provider_dependencies__)
    for dep in cls.__provider_dependencies__:
        deps.update(_get_all_dependencies(dep))
    return deps


def _sort_providers(
    providers: set[type["BaseProvider"]],
    cause: str | None = None,
) -> list[type["BaseProvider"]]:
    """Sort providers based on their dependencies using topologigal sort.
   
    This method analyzes the dependency graph and returns providers in the
    order they should be initialized. The dependencies always come before
    the providers that depend on them.

    Returns:
        list[type[BaseProvider]]: Providers sorted from first to last based
        on their initialization order.

    Raises:
        DependencyChainMismatch: When the dependency chain is invalid.

    Note:
        This is an internal method that implements Kahn's algorithm for
        topological sorting. The algorithm builds a dependency graph and
        processes nodes with no incoming edges, ensuring a valid
        initialization order.
    """

    # Build dependency graph
    graph = defaultdict(set)
    in_degree = defaultdict(int)

    for provider in providers:
        for dep in provider.__provider_dependencies__:
            graph[dep].add(provider)
            in_degree[provider] += 1

    # Topological sort
    result = []
    queue = [p for p in providers if in_degree[p] == 0]

    while queue:
        provider = queue.pop(0)
        result.append(provider)

        for dependent in graph[provider]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(result) != len(providers):
        raise DependencyChainMismatch(
            order=[p.__name__ for p in result],
            providers=[p.__name__ for p in providers],
            cause=cause,
        )

    return result


def _get_initialization_order(cls: type[_PT]) -> list[type["BaseProvider"]]:
    """Determine the correct initialization order for a given provider."""

    # Add all dependencies to the graph
    all_deps = _get_all_dependencies(cls)
    all_deps.add(cls)

    # Sort the providers based on their dependencies
    return _sort_providers(all_deps, cause=cls.__name__)


def _raise_on_self_dependency(
    cls: type[_PT],
    method: Callable[Concatenate[type[_PT], _P], _R],
) -> None:
    frame = inspect.currentframe()
    try:
        while frame:
            if frame.f_code.co_qualname.endswith(
                f"{cls.__name__}.provider_init",
            ):
                raise SelfDependency(cls.__name__, method.__name__)
            frame = frame.f_back
    finally:
        del frame


def _initialize_provider_chain(
    cls: type[_PT],
    requested_for: str,
) -> None:
    with _sync_init_lock:
        if cls.__provider_initialized__:
            return

        # Call metaclass setup hook if it is defined.
        if hasattr(cls.__class__, "_ensure_setup_hook_executed"):
            cls.__class__._ensure_setup_hook_executed()

        logger.debug(
            f"About to initialize provider {cls.__name__} because of: {requested_for}"
        )

        # Check for circular dependencies.
        _raise_on_circular_dependencies(cls)

        # Make sure all dependencies of this provider are initialized
        order = _get_initialization_order(cls)
        order_status = [
            f"{p.__name__}{' (initialized)' if p.__provider_initialized__ else ''}"
            for p in order
        ]
        logger.debug(
            f"Initialization order for provider {cls.__name__} is: "
            f"{', '.join(order_status)}"
        )
        for p in order:
            if not p.__provider_initialized__:
                try:
                    logger.debug(f"Initializing provider {p.__name__}...")
                    if hasattr(p, "provider_init"):
                        if callable(p.provider_init):
                            p.provider_init()
                    p.__provider_initialized__ = True
                    logger.info(f"Provider {p.__name__} initialized")
                except SelfDependency as e:
                    raise e
                except Exception as e:
                    raise InitError(
                        provider=cls.__name__,
                        exception=e,
                        cause=p.__name__,
                    ) from e


def _wrap_guarded_method(
    f: Callable[Concatenate[type[_PT], _P], _R],
) -> Callable[Concatenate[type[_PT], _P], _R]:
    if inspect.iscoroutinefunction(f):
        @wraps(f)
        async def async_wrapper(
            cls: type[_PT], *args: _P.args, **kwargs: _P.kwargs
        ) -> _R:  # type: ignore[override]
            if not getattr(cls, "__provider_initialized__", False):
                _raise_on_self_dependency(cls, f)
                _initialize_provider_chain(cls, requested_for=f.__name__)
            return await f(cls, *args, **kwargs)

        return async_wrapper  # type: ignore[return-value]

    @wraps(f)
    def sync_wrapper(cls: type[_PT], *args: _P.args, **kwargs: _P.kwargs) -> _R:  # type: ignore[override]
        if not getattr(cls, "__provider_initialized__", False):
            _raise_on_self_dependency(cls, f)
            _initialize_provider_chain(cls, requested_for=f.__name__)
        return f(cls, *args, **kwargs)

    return sync_wrapper  # type: ignore[return-value]
