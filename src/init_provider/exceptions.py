class ProviderError(Exception):
    """Base exception for all provider errors.

    This is the root exception class for all errors that can occur within
    the init-provider framework. Catching this exception will catch
    any framework-specific error.

    Use this when you want to handle any provider-related error generically,
    or when implementing error handling that should catch all framework errors.

    Example:
        ```python
        try:
            MyProvider.do_something()
        except ProviderError as e:
            # Handle any framework error
            logger.error(f"Provider framework error: {e}")
        ```
    """

    message: str
    """Human-readable error message describing what went wrong."""

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class CircularDependency(ProviderError):
    """Raised when circular dependencies are detected in the provider graph.

    This error occurs when providers have dependencies that form a cycle,
    making it impossible to determine a valid initialization order.

    The framework detects circular dependencies before initialization
    and provides information about which providers are involved in the cycle.

    Example:
        ```python
        @requires(ProviderB)
        class ProviderA(BaseProvider):
            pass

        @requires(ProviderA)  # Creates a cycle: A -> B -> A
        class ProviderB(BaseProvider):
            pass
        ```
    """

    def __init__(
        self,
        provider: str,
        recursion_stack: list[str],
    ):
        super().__init__(
            f"Circular dependency in provider {provider} within "
            f"recursion stack: {', '.join(recursion_stack)}"
        )


class DependencyChainMismatch(ProviderError):
    """Failed to determine a valid dependency order of providers.

    This error occurs when the framework is unable to determine a valid
    dependency chain for the providers. The length of the dependency chain
    does not match the number of all involved providers.
    """

    def __init__(
        self,
        order: list[str],
        providers: list[str],
        cause: str | None = None,
    ):
        if cause:
            super().__init__(
                "The length of the initialization chain for the provider "
                f"{cause} does not match the number of involved providers."
                f"Chain: {', '.join(order)}. "
                f"Providers: {', '.join(providers)}"
            )
        else:
            super().__init__(
                "The length of the dependency chain does not match "
                "the number of involved providers. "
                f"Chain: {', '.join(order)}. "
                f"Providers: {', '.join(providers)}"
            )


class SetupError(ProviderError):
    """Raised when the setup hook fails."""

    def __init__(self, exception: Exception):
        super().__init__(f"Error while invoking the setup hook: {exception}")


class DisposeError(ProviderError):
    """Raised when the @dispose hook or a provider_dispose() method fails."""

    def __init__(self, exception: Exception):
        super().__init__(f"Error while disposing: {exception}")


class InitError(ProviderError):
    """Raised when a provider fails to initialize properly.

    Example:

        ```python
        class DatabaseProvider(BaseProvider):
            def provider_init(self) -> None:
                # This might raise an exception
                self._connection = connect_to_database()
        ```
    """

    def __init__(
        self,
        provider: str,
        exception: Exception,
        cause: str | None = None,
    ):
        super().__init__(
            f"Failed to initialize {provider}"
            f"{' because of ' + cause if cause else ''}"
            f" ({type(exception).__name__}: {exception})"
        )


class SelfDependency(ProviderError):
    """Provider method was called from within provider_init().

    Calling provider method causes the provider and its dependencies to be
    initialized, if they weren't already. This is why calling a provider
    method inside provider_init() creates a self dependency loop.

    Methods decorated with @classmethod or @staticmethod can be called from
    within provider_init() without causing a self dependency loop, but cannot
    rely on uninitialized attributes.

    Example:
        ```python
        class UserProvider(BaseProvider):
            users: list[str]

            def provider_init(self) -> None:
                self.users = self.load_users() # ← This is fine.
                self.add_user("user3") # ← This will raise SelfDependency.

            @classmethod
            def load_users(cls) -> list[str]:
                return ["user1", "user2"]

            def add_user(self, user: str) -> None:
                self.users.append(user)
        ```
    """

    def __init__(self, name: str, method: str):
        super().__init__(
            f"Method {method} was called in provider_init() "
            f"of its class {name}"
        )


class AttributeNotInitialized(ProviderError):
    """Raised when a provider attribute is accessed before being initialized.

    This error occurs when trying to use a provider attribute that hasn't been
    initialized yet.
    """

    def __init__(self, provider: str, attr: str):
        super().__init__(f"Provider {provider} attribute {attr} was never initialized.")


class ProviderDefinitionError(ProviderError):
    """Raised when a provider is defined incorrectly."""
