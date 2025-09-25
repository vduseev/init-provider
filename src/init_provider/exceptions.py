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


class InitializationOrderMismatch(ProviderError):
    """Failed to determine a valid initialization order of providers.

    This error occurs when the framework is unable to determine a valid
    initialization order for the provider and its dependencies. The number
    of all dependencies within the initialization chain does not match the
    the initialization order length.
    """

    def __init__(self, provider: str, order: list[str], dependencies: list[str]):
        super().__init__(
            f"Number of dependencies for provider {provider} does not match "
            f"the initialization order. Order: {', '.join(order)}. "
            f"Dependencies: {', '.join(dependencies)}"
        )


class SetupError(ProviderError):
    """Raised when a provider fails to setup properly.

    This error occurs when the provider's setup() method raises an exception.
    """

    def __init__(self, exception: Exception):
        super().__init__(f"Error while invoking the setup function: {exception}")


class ProviderInitializationError(ProviderError):
    """Raised when a provider fails to initialize properly.

    This error occurs when the provider's __init__() method raises an exception.

    Example:
        ```python
        class DatabaseProvider(BaseProvider):
            def __init__(self) -> None:
                # This might raise an exception
                self._connection = connect_to_database()
        ```
    """

    def __init__(self, provider: str, dep: str, exception: Exception):
        super().__init__(
            f"Failed to initialize provider {provider}"
            f"{' because of dependency ' + dep if dep != provider else ''}"
            f" ({type(exception).__name__}: {exception})"
        )


class SelfDependency(ProviderError):
    """Provider method decorated with @init was called from within initialize().

    Calling provider class method decorated with @init causes the provider
    and its dependencies to be initialized, if they weren't already. Calling
    an @init decorated method from within __init__() creates a self
    dependency loop.

    Methods decorated with @classmethod or @staticmethod can be called from
    within __init__() without causing a self dependency loop, but cannot
    rely on uninitialized attributes or other @init decorated methods.

    Example:
        ```python
        class UserProvider(BaseProvider):
            users: list[str]

            def __init__(self) -> None:
                self.users = self.load_users() # ← This is fine.
                self.add_user("user3") # ← This will raise SelfDependency.

            @classmethod
            def load_users(cls) -> list[str]:
                return ["user1", "user2"]

            @init
            def add_user(self, user: str) -> None:
                self.users.append(user)
        ```
    """

    def __init__(self, name: str, method: str):
        super().__init__(
            f"Provider method {method} decorated with @init was called "
            f"from within __init__() of its class {name}"
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


class InitCalledDirectly(ProviderError):
    """Raised when a provider's __init__() method is called directly."""

    def __init__(self, provider: str):
        super().__init__(f"Cannot call method {provider}.__init__() directly.")
