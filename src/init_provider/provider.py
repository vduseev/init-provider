from abc import ABC

from ._internal._metaclass import ProviderMetaclass


__all__ = ["BaseProvider", "ProviderMetaclass"]


class BaseProvider(ABC, metaclass=ProviderMetaclass):
    """Provider class.

    Only one instance of each provider exists within the same process.
    Providers cannot be instantiated but can define class variables and
    class methods. The values of class variables can be lazily initialized
    and disposed off at runtime.

    Providers can depend on each other.

    Raises:
        RuntimeError: When attempting to create an instance of a provider.

    Example:
    
        ```python
        @requires(DatabaseProvider, CacheProvider)
        class UserCache(BaseProvider):
            users: dict[int, User]
            refresh_timestamp: datetime
            refresh_interval: timedelta = timedelta(minutes=10)

            def provider_init(self) -> None:
                # Load initial data
                self.refresh()

            def provider_dispose(self) -> None:
                # Cache users on application exit
                CacheProvider.store(self.users)

            def get_user(self, user_id: int) -> User | None:
                if self.refresh_timestamp < datetime.now() - self.refresh_interval:
                    self.refresh()
                return self.users.get(user_id)

            @classmethod
            def refresh(cls) -> None:
                cls.users = DatabaseProvider.load_all_users()
                cls.refresh_timestamp = datetime.now()
        ```
    """

    __provider_initialized__: bool = False
    __provider_disposed__: bool = False
    __provider_dependencies__: set[type["BaseProvider"]] = set()
    __provider_guarded_attrs__: set[str] = set()

    def __new__(cls, *args, **kwargs) -> "BaseProvider":
        """Prevent instantiation of providers.

        This method is overridden to prevent creating instances of providers.
        The provider pattern is enforced by making all functionality available
        through class methods only.

        Args:
            *args: Any positional arguments (ignored).
            **kwargs: Any keyword arguments (ignored).

        Raises:
            RuntimeError: Always raised to prevent instantiation.

        Example:
            ```python
            # This will raise RuntimeError
            provider = MyProvider()

            # Use class methods instead
            MyProvider.some_method()
            ```
        """
        raise RuntimeError(
            f"{cls.__name__} is a provider and cannot be instantiated. "
            "Use class methods directly instead."
        )

    def provider_init(self) -> None:
        """Initialize the provider lazily."""
        pass

    def provider_dispose(self) -> None:
        """Dispose of the provider."""
        pass
