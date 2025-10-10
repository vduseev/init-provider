import inspect
import logging
from collections.abc import Callable
from typing import (
    ParamSpec,
    TypeVar,
)

from .exceptions import ProviderDefinitionError
from .provider import BaseProvider, ProviderMetaclass


_P = ParamSpec("_P")
_R = TypeVar("_R")
_R_co = TypeVar("_R_co", covariant=True)
_PT = TypeVar("_PT", bound=BaseProvider)


logger = logging.getLogger("init_provider")
__all__ = ["requires", "setup"]


def requires(
    *dependencies: type[BaseProvider],
) -> Callable[[type[_PT]], type[_PT]]:
    """Declare dependencies between providers.

    This decorator is used to specify which other providers a provider depends on.
    The framework uses this information to ensure dependencies are initialized
    in the correct order before the provider itself is initialized.

    Args:
        dependencies: Variable number of provider classes that this provider
        depends on. Each must be a subclass of BaseProvider.

    Note:
        - Circular dependencies will be detected and raise CircularDependency
        - Dependencies are initialized recursively
        - The order of dependencies in the decorator doesn't matter

    Single dependency:

        @requires(DatabaseProvider)
        class UserProvider(BaseProvider):
            pass

    Multiple dependencies:

        @requires(DatabaseProvider, CacheProvider, AuthProvider)
        class UserProvider(BaseProvider):
            pass

    Chained dependencies:

        ```python
        # AuthProvider depends on DatabaseProvider
        @requires(DatabaseProvider)
        class AuthProvider(BaseProvider):
            pass

        # UserProvider depends on AuthProvider
        # (and transitively on DatabaseProvider)
        @requires(AuthProvider)
        class UserProvider(BaseProvider):
            pass
        ```
    """

    def decorator(cls: type[_PT]) -> type[_PT]:
        if not issubclass(cls, BaseProvider):
            raise ProviderDefinitionError(
                f"Cannot use @requires on {cls.__name__} because "
                "it is not a subclass of BaseProvider"
            )

        deps = set()
        for dep in dependencies:
            if not issubclass(dep, BaseProvider):
                raise ProviderDefinitionError(
                    f"Cannot use {dep.__name__} as a dependency because "
                    "it is not a subclass of BaseProvider"
                )
            deps.add(dep)
        cls.__provider_dependencies__ = deps
        return cls

    return decorator


def setup(func: Callable[[], _R_co]) -> Callable[[], _R_co]:
    """Decorator to mark a function as the provider setup function.

    The setup function is called exactly once at the start of the application,
    when the first call to any provider is made.

    The hook can optionally return a result, which will be logged at the
    INFO level.

    Simple hook:

        @setup
        def configure():
            logging.basicConfig(level=logging.INFO)
            warnings.filterwarnings("ignore", module="some_module")

    Hook with a result:

        @setup
        def configure() -> str:
            neomodel.config.DATABASE_URL = "bolt://neo4j:neo4j@localhost:7687"
            return "Configuration completed."
    """

    # Cannot register functions that expect arguments.
    if inspect.getfullargspec(func).args:
        raise ProviderDefinitionError(
            f"{func.__qualname__} is a function that expects arguments and cannot be used as a setup function"
        )

    ProviderMetaclass.__provider_setup_hook__ = func  # type: ignore[attr-defined]
    logger.debug(f"Setup hook registered: {func.__qualname__}")
    return func


def dispose(func: Callable[[], _R_co]) -> Callable[[], _R_co]:
    """Decorator to mark a function as the provider dispose function.

    The dispose function is called exactly once at the end of the application,
    when the last call to any provider is made.

    The hook can optionally return a result, which will be logged at the
    INFO level.

    Simple hook:

        @dispose
        def destroy():
            os.unlink("database.db")

    Hook with a result:

        @dispose
        def destroy() -> str:
            os.unlink("database.db")
            return "Database destroyed."
    """
    # Cannot register functions that expect arguments.
    if inspect.getfullargspec(func).args:
        raise ProviderDefinitionError(
            f"{func.__qualname__} is a function that expects arguments and cannot be used as a dispose function"
        )

    ProviderMetaclass.__provider_dispose_hook__ = func  # type: ignore[attr-defined]
    logger.debug(f"Dispose hook registered: {func.__qualname__}")
    return func
