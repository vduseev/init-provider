<h1><code>init-provider</code></h1>

Initialization and instance provider framework for Python.

![PyPI - Version](https://img.shields.io/pypi/v/init-provider)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/init-provider)
![PyPI - Status](https://img.shields.io/pypi/status/init-provider)
![PyPI - License](https://img.shields.io/pypi/l/init-provider)

* **Init order**: for example, `ProviderA` depends on `ProviderB`.
* **Reusable objects**: expose instances of Settings or a Connection Pool.
* **Business logic**: clean internal APIs.
* **Entry point**: use for a CLI, Web API, background worker, etc.

- [Quick start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Inherit from `BaseProvider`](#inherit-from-baseprovider)
  - [Store in class variables](#store-in-class-variables)
  - [Initialize using `__init__()`](#initialize-using-__init__)
  - [Dispose using `__del__()`](#dispose-using-__del__)
  - [Decorate methods using `@init`](#decorate-methods-using-init)
  - [Dependencies using `@requires`](#dependencies-using-requires)
- [Examples](#examples)
  - [Weather service](#weather-service)
  - [User service](#user-service)
- [Troubleshooting](#troubleshooting)
  - [Enable logging](#enable-logging)
- [Design choices](#design-choices)
- [License](#license)

## Quick start

Below is a full runnable example that uses everything in this library.

```python
import logging
from pathlib import Path
from init_provider import BaseProvider, init, requires, setup, dispose


@setup
def configure() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)-8s %(name)-15s %(message)s",
    )
    if not Path("file.txt").exists():
        logging.info("> file.txt does not yet exist")


@dispose
def cleanup() -> None:
    if not Path("file.txt").exists():
        logging.info("> file.txt no longer exist")


class Storage(BaseProvider):
    path = Path("file.txt")

    def __init__(self):
        logging.info("> create Storage")
        self.path.touch()

    def __del__(self):
        logging.info("> dispose of Storage")
        self.path.unlink()

    @init
    def write(self, content: str) -> None:
        logging.info(f"> write to Storage: {content}")
        self.path.write_text(content)

    @init
    def read(self) -> str:
        data = self.path.read_text()
        logging.info(f"> read from Storage: {data}")
        return data


@requires(Storage)
class Namer(BaseProvider):
    def __init__(self) -> None:
        logging.info("> create Namer")
        Storage.write("Bobby")


@requires(Namer)
class Greeter(BaseProvider):
    define_at_runtime: str

    def __init__(self):
        logging.info("> create Greeter")
        self.define_at_runtime = Storage.read()

    @init
    def greet(self) -> None:
        print(f">>> Hello, {self.define_at_runtime}!")


if __name__ == "__main__":
    Greeter.greet()
```

Output:

```shell
$ uv run python examples/full_example.py
INFO     root            > file.txt does not yet exist
INFO     init_provider   Setup hook executed.
DEBUG    init_provider   About to initialize provider Greeter because of: greet
DEBUG    init_provider   Initialization order for provider Greeter is: Storage, Namer, Greeter
DEBUG    init_provider   Initializing provider Storage...
INFO     root            > create Storage
INFO     init_provider   Provider Storage initialized
DEBUG    init_provider   Initializing provider Namer...
INFO     root            > create Namer
INFO     root            > write to Storage: Bobby
INFO     init_provider   Provider Namer initialized
DEBUG    init_provider   Initializing provider Greeter...
INFO     root            > create Greeter
INFO     root            > read from Storage: Bobby
INFO     init_provider   Provider Greeter initialized
>>> Hello, Bobby!
DEBUG    init_provider   Provider dispose call order: ['Greeter', 'Namer', 'Storage']
INFO     init_provider   Dispose hook for Greeter was executed.
INFO     init_provider   Dispose hook for Namer was executed.
INFO     root            > dispose of Storage
INFO     init_provider   Dispose hook for Storage was executed.
INFO     root            > file.txt no longer exist
INFO     init_provider   Dispose hook executed.
```

## Installation

Using `pip`:

```shell
pip install init-provider
```

Using `uv`:

```shell
uv add init-provider
```

## Usage

Providers are just classes. In fact, they look a lot like a `dataclass` but
with three major differences:

1. You do not need to instantiate the provider class.
2. Providers can depend on each other.
3. Calling any method or attribute of a provider will trigger initialization.

### Inherit from `BaseProvider`

Create a class that inherits from `BaseProvider`. This automatically
registers your provider inside the framework. 

```python
from init_provider import BaseProvider

class WeatherProvider(BaseProvider):
    """Fetch weather data from the API."""
```

### Store in class variables

Use class variables just like you would define fields in a `dataclass`.

```python
# ...
class WeatherProvider(BaseProvider):
    # ...
    _base_url: str = "https://theweather.com/api"
```

*Note*: `init_provider` doesn't care about underscores in variable and
method names. It will expose them all the same.

### Initialize using `__init__()`

When you need to initialize the provider, you can focus on **what** needs to
be initialized rather than **when** it needs to be initialized.

Not all providers require initialization, but when they do, you can define
it inside the `__init__()` method.

For example, you might want to initialize a reusable [aiohttp][1] session
during runtime, when the asyncio event loop is already running.

```python
# ...
import asyncio
from aiohttp import ClientSession

class WeatherProvider(BaseProvider):
    # ...
    _session: ClientSession

    def __init__(self) -> None:
        self._session = ClientSession()

if __name__ == "__main__":
    if WeatherProvider._session.closed:
        print("Session is still closed")
```

*Note 1*: in the example aboev, the `_session` variable is declared without
a value. The initialization is done inside the `__init__()`.
Trying to access the `_session` object will trigger the initialization chain.

*Note 2*: The `__init__` method of the owner class is the only place
where initialization will not be triggered, when the object is accessed.

*Warning*: Declaring a class variable with a default value will mean that it's

### Dispose using `__del__()`

If you need to, you can dispose of resources in the `__del__()` method.
An example of this is closing a database connection.

### Decorate methods using `@init`

Providers are great for encapsulating reusable business logic in a methods.
Every provider method decorated with `@init` becomes guarded. Guarded
methods cause initialization of the provider chain when they are called.

*Note*: Reserved methods that contain double underscore (`__`) and methods
decorated with `@staticmethod` or `@classmethod` will not be guarded.

```python
from init_provider import BaseProvider

class WeatherProvider(BaseProvider):
    # ...
    @init
    def get_url(cls, path: str) -> str:
        return f"{cls._base_url}/{path}"
```

### Dependencies using `@requires`

Use the `@requires` decorator to list other providers that the
`WeatherProvider` depends on.

```python
@requires(GeoProvider)
class WeatherProvider(BaseProvider):
    # ...
```

## Examples

### Weather service

```python
import asyncio
import logging
from aiohttp import ClientSession
from init_provider import BaseProvider, init, requires

logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")


class GeoService(BaseProvider):
    @init
    def city_coordinates(self, name: str) -> tuple[float, float]:
        """Returns the latitude and longitude of a city."""
        if name == "London":
            return 51.509, -0.118  # London, UK
        elif name == "New York":
            return 40.7128, -74.0060  # New York, USA
        raise ValueError(f"Unknown city: {name}")


@requires(GeoService)
class WeatherService(BaseProvider):
    _session: ClientSession
    _base_url: str = "https://api.open-meteo.com/v1/forecast/"

    def __init__(self) -> None:
        # Properly initializing aiohttp session at runtime, when the
        # default asyncio loop is already running.
        self._session = ClientSession(self._base_url)

    @classmethod
    async def close(cls):
        await cls._session.close()

    @init
    async def temperature(self, city: str) -> float:
        lat, lon = GeoService.city_coordinates(city)
        params: dict[str, str | float] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m",
        }
        async with self._session.get(self._base_url, params=params) as resp:
            data = await resp.json()
            return data["hourly"]["temperature_2m"][0]


async def main():
    # This will immediately initialize WeatherService and its dependencies,
    # because we have attempted to access the _session property.
    print(f"Is session closed: {WeatherService._session.closed}")

    # Subsequent calls do not reinitialize the provider.
    london = await WeatherService.temperature("London")
    new_york = await WeatherService.temperature("New York")
    print(f"London: {london:.2f}°C")
    print(f"New York: {new_york:.2f}°C")

    # Release the resources. Normally, this would be implemented in the
    # __del__() method of the provider, but the async client must be closed
    # inside the same event loop it was created.
    await WeatherService.close()
    print(f"Is session closed: {WeatherService._session.closed}")


if __name__ == "__main__":
    asyncio.run(main())
```

Output:

```shell
$ uv run python examples/weather_service.py
DEBUG    Using selector: KqueueSelector
DEBUG    About to initialize provider WeatherService because of: _session
DEBUG    Initialization order for provider WeatherService is: GeoService, WeatherService
DEBUG    Initializing provider GeoService...
INFO     Provider GeoService initialized
DEBUG    Initializing provider WeatherService...
INFO     Provider WeatherService initialized
Is session closed: False
London: 11.40°C
New York: 16.50°C
Is session closed: True
DEBUG    Provider dispose call order: ['WeatherService', 'GeoService']
INFO     Dispose hook for WeatherService was executed.
INFO     Dispose hook for GeoService was executed.
```

### User service 

```python
import logging
import os
import sqlite3
import warnings
from contextlib import contextmanager
from typing import Generator

from init_provider import BaseProvider, init, requires, setup


# (Optional) Declare a setup function to be executed once per application
# process before any provider is initialized.
@setup
def configure():
    log_format = "%(levelname)-8s %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=log_format)
    warnings.filterwarnings("ignore", module="some_module")


# ↓ Basic provider. Exposes 1 attribute: connection
class DatabaseService(BaseProvider):
    """Single instance of connection ot SQLite."""

    # ↓ Any attempt to access a provider attribute outside
    #   of __init__() will cause the provider to be initialized.
    db_path: str

    # ↓ Initialize, just like in a dataclass. But you NEVER
    #   have to create an instance of a provider manually.
    def __init__(self) -> None:
        # Run some one-time initialization logic
        self.db_path = "database.db"

        # Initialize the database. This will only be done once
        # across the entire lifecycle of the application.
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            # Create a table
            cur.execute(
                "CREATE TABLE IF NOT EXISTS users "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)"
            )
            # Add mock data
            cur.executemany(
                "INSERT INTO users (name) VALUES (?)",
                [("Alice",), ("Bob",)],
            )
            conn.commit()

    # ↓ Declare a dispose method to be called before the application exits.
    def __del__(self):
        os.unlink(self.db_path)

    # ↓ Any call to the `conn` method will cause the
    #   provider to be initialized, if not already done.
    @init
    @contextmanager
    def conn(self) -> Generator[sqlite3.Connection, None, None]:
        """One-time connection to the database."""
        with sqlite3.connect(self.db_path) as conn:
            yield conn


# ↓ This one depends on another provider.
@requires(DatabaseService)
class UserService(BaseProvider):
    """Intenal API class to abstract the Users data layer."""

    # → Notice: NO __init__() method here! Because there is nothing
    #   to initialize inside this specific provider itself.

    # ↓ Require initialization of all dependencies when this
    #   method is called.
    @init
    def get_name(self, user_id: int) -> str | None:
        """Get user name based on ID"""

        # ↓ Access the method from another provider
        with DatabaseService.conn() as conn:
            cur = conn.cursor()
            if result := cur.execute(
                "SELECT name FROM users WHERE id = ?", (user_id,)
            ).fetchone():
                return result[0]
            else:
                return None


if __name__ == "__main__":
    # ↓ This will cause the chain of dependencies to be
    #   initialized in the following order:
    #   1. configure() function will be called
    #   2. DatabaseService
    database_path = DatabaseService.db_path
    print(f">> {database_path}")

    # ↓ This will only initialize the UserService, because
    #   its dependencies are already initialized.
    user_1 = UserService.get_name(1)
    print(f">> {user_1}")

    # ↓ Let's get the name of another user. NOTHING extra will be
    #   done because the dependency graph is already initialized.
    user_2 = UserService.get_name(2)
    print(f">> {user_2}")
```

Output:

```shell
$ uv run python examples/user_service.py
INFO     Setup hook executed.
DEBUG    About to initialize provider DatabaseService because of: db_path
DEBUG    Initialization order for provider DatabaseService is: DatabaseService
DEBUG    Initializing provider DatabaseService...
INFO     Provider DatabaseService initialized
DEBUG    About to initialize provider UserService because of: get_name
DEBUG    Initialization order for provider UserService is: DatabaseService (initialized), UserService
DEBUG    Initializing provider UserService...
INFO     Provider UserService initialized
>> database.db
>> Alice
>> Bob
DEBUG    Provider dispose call order: ['UserService', 'DatabaseService']
INFO     Dispose hook for UserService was executed.
INFO     Dispose hook for DatabaseService was executed.
```

## Troubleshooting

### Enable logging

The framework produces logs tied to the `init_provider` module. Make sure
the logs from this module are not suppressed in the global `logging`
configuration.

The easiest way to enable logging is to set the logging level to `DEBUG`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Which will allow you to see what `init_provider` is doing:

```shell
$ uv run python examples/weather_service.py
DEBUG    About to initialize provider WeatherService because of: session
DEBUG    Initialization order for provider WeatherService is: GeoService, WeatherService
DEBUG    Initializing provider GeoService...
INFO     Provider GeoService initialized successfully
DEBUG    Initializing provider WeatherService...
```

## Design choices

* `BaseProvider` inheritance instead of `@provider` decorator.

  If a decorator approach was chosen to mimic the `@dataclass` approach,
  then the dependencies would have to be specified using another
  decorator (ugly) or inside the class body (awkward).

  That's why the choice was made towards inheritance. It is very familiar
  to `pydantic` users and allows the list of dependencies to be specified
  elegantly using the `@requires` decorator sitting on top of the class
  definition.

* `__init__()` as initialization method instead of `provider_init()`.

  The choice was made use native `__init__()`, because that's where any
  developer would expect to find the initialization code. Introducing
  a separate `provider_init()` method would inflict additional cognitive
  load for no real benefit.

  There could be one justification for custom methods: async
  initialization. In that case, two base classes would exist:
  `BaseProvider` and `AsyncBaseProvider`. Each would define
  `provider_init()` and `provider_dispose()` methods as normal functions
  or as coroutines. However, the whole async approach had to be discarded
  because of incompatibility with guarded class variables (see below).

* `__del__()` as disposal method.

  While the `__del__()` method is rarely used and is unfamiliar to most
  Python developers, it is the least awkard way to define a sort of a 
  destructor for a provider.

  Even though the **true** implementation of `__del__()` explicitly
  states the it is guaranteed to be called, it does not affect the
  provider, because we hijack both the `__init__` and `__del__` and they
  are guaranteed to be called.

  An alternative would be to force the developers to deal with
  restrictive `weakref.finalize` functions which are hard to use because
  you can't pass a reference to the instance you want to dispose of
  as an argument to the finalizer.

* `@init`

  While technically the `@init` decorator for guarded class methods is
  not required at all, it has been added for type checking purposes.

  Without `@init`, we could forcibly convert all methods of the
  class into `classmethod`s, adding dependency initialization checks
  around them and allowing them to be called without an instance.

  ```python
  """Without @init but with failing type checks"""

  class MyProvider(BaseProvider):
      def greet(self, name: str):
          print(f"Hello, {name}!")

  if __name__ == "__main__":
      MyProvider.greet("World")
  ```

  That works and looks very nice, but the static type analyzers go crazy.
  They expect the `greet` method to receive 2 arguments, but we only
  pass one.

  An alternative would be to overhaul the entire provider protocol and
  require an actual instance creation. However, under the hood, we
  could always return a singleton instance from the `__new__` method.

  ```python
  """Alternative to @init with instance creation"""

  class MyProvider(BaseProvider):
      def greet(self, name: str):
          print(f"Hello, {name}!")

  if __name__ == "__main__":
      MyProvider().greet("World")
  ```

  That would work too, but it is so awkward that it's painful to use.
  This is not Java and in Python nobody just creates instances left and
  right for no good reason. Any Python developer that reads the code 
  above would immediately assume that a one-time instance of `MyProvider`
  was created and would be destroyed soon, which seems counter 
  intuitive.

  There is, however, still one reason for `MyProvider()` approach
  to remain on the table: **AI coding assistant and tab-completion.**
  During tests, most of the time, when not surrounded by examples or
  without explicit instructions, they attempt to write
  `MyProvider().greet("World")` instead of `MyProvider.greet("World")`.
  If this will remain the case, **the library might eventually switch
  to this awkward but practical approach.**

  That's why we have the `@init` decorator. It's not there to make
  providers and guarded methods work. It is there to solve the type
  checking while being the least awkward approach.

* No `async` initialization or disposal.

  There are use cases where we'd want both the `__init__` and
  `__dispose__` to be async and the whole initialization and disposal of
  a particular provider to happen inside an already running event loop.

  For example, an async http client:

  ```python
  import asyncio
  import aiohttp

  class MyProvider(BaseProvider):
      client: aiohttp.ClientSession

      async def __init__(self):
          self.client = aiohttp.ClientSession()

      async def __dispose__(self):
          await self.client.close()
  ```

  That would look and feel amazing. We could impose a rule that async
  providers can depend on sync and other async providers. But the sync
  providers would only be allowed to depend on other sync providers,
  which would address most concerns around async initialization order.

  Unfortunately, this whole logic breaks down the moment we attempt to
  implement guarded class variables.

  Imagine a function which accesses the `client` class variable above
  for some purposes:

  ```python
  async def main():
    await MyProvider.client.get("https://example.com")

  if __name__ == "__main__":
    asyncio.run(main())
  ```

  As soon as `MyProvider.client` code is reached, the provider library
  must detect that an attempt to read a guarded class variable is made.
  It checks whether the provider is initialized or not. If it is not,
  it initializes all of the dependencies of this provider and the
  provider itself. Once that's done, the `client` value, already
  initialized at this point, is returned.

  The only way to implement this detection and lazy initialization
  at access time is to override the `__getattribute__` method.
  
  In a situation where provider's initialization logic is asynchronous
  the provider chain initialization funciton would have to be called
  with `await`. But that would be impossible inside a normal function
  or method, such as `__getattribute__`.

  Therefore, a tradeoff must be made. Either we want guarded class
  variables that are lazily initialized at runtime. Or we want
  providers that can have asynchronous initialization logic.
  Can't have both.

  In this library, the choice was made in favor of the former. Lazily
  initialized guarded class variables are too convenient to give them
  up.

## License

Licensed under the [Apache-2.0 License](./LICENSE).

[1]: https://docs.aiohttp.org/
[2]: https://martinfowler.com/eaaCatalog/repository.html