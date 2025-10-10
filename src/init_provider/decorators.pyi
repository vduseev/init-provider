from typing import (
    Callable,
    ParamSpec,
    TypeVar,
)

from .provider import BaseProvider

_PT = TypeVar("_PT", bound=BaseProvider)
"""Type of the BaseProvider class"""
_P = ParamSpec("_P")
"""Parameters of the decorated method, except cls itself."""
_T_co = TypeVar("_T_co", covariant=True)
_R_co = TypeVar("_R_co", covariant=True)
"""Return type of the decorated method (covariant).

Covariant, because the decorator only uses _R_co to define what
is being returned. It doesn't modify it or accept it as an argument.
"""


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
    ...

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
    ...

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
    ...
