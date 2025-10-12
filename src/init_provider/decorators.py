import inspect
import logging
from collections.abc import Callable
from typing import (
    ParamSpec,
    TypeVar,
    Concatenate,
)

from .exceptions import ProviderDefinitionError
from .provider import BaseProvider, ProviderMetaclass
from ._internal._utils import _wrap_guarded_method


_P = ParamSpec("_P")
_R = TypeVar("_R")
_R_co = TypeVar("_R_co", covariant=True)
_PT = TypeVar("_PT", bound=BaseProvider)


logger = logging.getLogger("init_provider")
__all__ = ["init", "requires", "setup"]


def init(
    func: Callable[Concatenate[type[_PT], _P], _R] | classmethod,
    /,
) -> classmethod:
    """Ensure provider and dependencies are initialized when this method is called.

    This decorator is equivalent to @classmethod, but it also ensures that
    the provider and its dependencies are initialized before the method is
    executed.

    Args:
        func: The method to be guarded.

    Note:
        - Works with both synchronous and asynchronous methods
        - Every provider is only ever initialized once
        - Cannot be called from within the same provider's __init__() method

    Examples:

        Basic usage:
        ```python
        @requires(DatabaseProvider)
        class UserProvider(BaseProvider):
            @init
            def get_user(self, user_id: int) -> User:
                # DatabaseProvider guaranteed to be initialized here
                return DatabaseProvider.fetch_user(user_id)
        ```

        Async method:
        ```python
        @requires(APIProvider)
        class WeatherProvider(BaseProvider):
            @init
            async def get_weather(self, city: str) -> Weather:
                # APIProvider guaranteed to be initialized here
                return await APIProvider.fetch_weather(city)
        ```

        Multiple dependencies and context manager:
        ```python
        @requires(DatabaseProvider, CacheProvider, MetricsProvider)
        class UserProvider(BaseProvider):
            @init
            @asynccontextmanager
            async def get_user_with_metrics(self, user_id: int) -> AsyncGenerator[User, None]:
                # All three providers

                cached = CacheProvider.get(f'user:{user_id}')
                if cached:
                    yield cached

                user = DatabaseProvider.fetch_user(user_id)
                CacheProvider.set(f'user:{user_id}', user)
                yield user
        ```
    """
    func_ = func.__func__ if isinstance(func, classmethod) else func
    if func_.__name__ in ("__init__", "__del__"):  # type: ignore[unresolved-attribute]
        raise ProviderDefinitionError(
            f"{func_.__qualname__} is a reserved method "  # type: ignore[unresolved-attribute]
            "and cannot be decorated with @init."
        )

    guarded_func = _wrap_guarded_method(func_)
    return classmethod(guarded_func)


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
            f"{func.__qualname__} is a function that expects "  # type: ignore[unresolved-attribute]
            "arguments and cannot be used as a setup function"
        )

    ProviderMetaclass.__provider_setup_hook__ = func  # type: ignore[attr-defined]
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
            f"{func.__qualname__} is a function that expects "  # type: ignore[unresolved-attribute]
            "arguments and cannot be used as a dispose function"
        )

    ProviderMetaclass.__provider_dispose_hook__ = func  # type: ignore[attr-defined]
    return func
