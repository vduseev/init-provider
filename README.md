<h1><code>init-provider</code></h1>

Initialization and instance provider framework for Python.

![PyPI - Version](https://img.shields.io/pypi/v/init-provider)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/init-provider)
![PyPI - Status](https://img.shields.io/pypi/status/init-provider)
![PyPI - License](https://img.shields.io/pypi/l/init-provider)

- [Use cases](#use-cases)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Design patterns](#design-patterns)
- [Usage](#usage)
  - [Inherit `BaseProvider`](#inherit-baseprovider)
  - [Store state in class variables](#store-state-in-class-variables)
  - [Initialize inside `provider_init()`](#initialize-inside-provider_init)
  - [Add business logic](#add-business-logic)
  - [Specify dependencies with `@requires`](#specify-dependencies-with-requires)
- [Examples](#examples)
  - [Weather service](#weather-service)
  - [User service](#user-service)
- [Troubleshooting](#troubleshooting)
  - [Enable logging](#enable-logging)
- [License](#license)

## Use cases

* *Solve initialization hell*: Declare what depends on what and **forget about it**!
* *Share object instances*: Expose a reusable instance of Settings or a Connection Pool.
* *Business logic*: Implement clean internal APIs.
* *Entry point*: Define an entry point for your CLI, Web API, background worker, etc.

## Quick Start

Runnable end‑to‑end example:

```python
from init_provider import BaseProvider, requires

class Config(BaseProvider):
    message: str

    def provider_init(self) -> None:
        self.message = "Hello"

@requires(Config)
class Greeter(BaseProvider):
    def greet(self, name: str) -> str:
        return f"{Config.message}, {name}!"

if __name__ == "__main__":
    print(Greeter.greet("World"))
```

## Installation

* Available on PyPI.
* Pure Python with zero runtime dependencies.
* Supports Python 3.10+.

```bash
# Using pip
pip install init-provider

# Using uv
uv add init-provider
```

## Design patterns

Write clean, testable, and maintainable code. `init-provider` lets you
implement any of the common design patterns below in a very concise way:

* [Repository](https://martinfowler.com/eaaCatalog/repository.html): Abstract the data access layer (S3, SQL, REST, etc) and return Models.
* Controller: Modify internal state based on requests from user or other systems.
* Service: Implement business logic.
* Singleton: Provide a single instance of a class, such as Settings.

## Usage

Providers are just classes. In fact, they look a lot like a `dataclass` but
with three major differences:

1. You do not need to instantiate the provider class.
2. Providers can depend on each other.
3. Calling any method or attribute of a provider will trigger initialization.

### Inherit `BaseProvider`

Create a class that inherits from `BaseProvider`. This automatically
registers your provider inside the framework. 

```python
from init_provider import BaseProvider

class WeatherProvider(BaseProvider):
    """Fetch weather data from the API."""
```

### Store state in class variables

Use class variables just like you would in a `dataclass`.

```python
# ...
class WeatherProvider(BaseProvider):
    # ...
    _base_url: str = "https://theweather.com/api"
```

*Note*: `init_provider` doesn't care about underscores in variable and
method names. It will expose them all the same.

### Initialize inside `provider_init()`

When you need to initialize the provider, you can focus on **what** needs to
be initialized rather than **when** it needs to be initialized.

Not all providers require initialization, but when they do, you can define
it inside the `provider_init()` method.

For example, you might want to initialize a reusable [aiohttp][1] session
during runtime, when the asyncio event loop is already running.

```python
# ...
import asyncio
from aiohttp import ClientSession

class WeatherProvider(BaseProvider):
    # ...
    _session: ClientSession

    def provider_init(self) -> None:
        self._session = ClientSession()

if __name__ == "__main__":
    if WeatherProvider._session.closed:
        print("Session is still closed")
```

*Note 1*: in the example aboev, the `_session` variable is declared without
a value. The initialization is done inside the `provider_init()`.
Trying to access the `_session` object will trigger the initialization chain.

*Note 2*: The `provider_init` method of the owner class is the only place
where initialization will not be triggered, when the object is accessed.

*Warning*: Declaring a class variable with a default value will mean that it's

### Add business logic

Providers are great for encapsulating reusable business logic in a methods.
Every method of the provider automatically becomes a guarded method. Guarded
methods cause initialization of the provider chain, when they are called.

*Note*: Reserved methods that contain double underscore (`__`) and methods
decorated with `@staticmethod` or `@classmethod` will not be guarded.

```python
from init_provider import BaseProvider

class WeatherProvider(BaseProvider):
    # ...
    @classmethod
    def get_url(cls, path: str) -> str:
        return f"{cls._base_url}/{path}"
```

### Specify dependencies with `@requires`

Use the `@requires` decorator to list other providers that the
`WeatherProvider` depends on.

```python
@requires(GeoProvider)
class WeatherProvider(BaseProvider):
    # ...
```

<a id="guard-methods"></a>
Finally, guard the class methods that need everything to be initialized
before they are called with the `@guarded` decorator.

```python
@requires(GeoProvider)
class WeatherProvider(BaseProvider):
    # ...
    @guarded
    def get_weather(cls, city: str) -> dict:
        return cls._session.get(cls.get_url(f"weather?q={city}")).json()
```

## Examples

### Weather service

```python
import asyncio
import logging
from aiohttp import ClientSession
from init_provider import BaseProvider, requires

logging.basicConfig(level=logging.DEBUG, format="%(levelname)-8s %(message)s")

class GeoService(BaseProvider):
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
    
    def provider_init(self) -> None:
        # Properly initializing aiohttp session at runtime, when the
        # default asyncio loop is already running.
        self._session = ClientSession(self._base_url)

    @classmethod
    async def close(cls):
        await cls._session.close()

    async def temperature(self, city: str) -> float:
        lat, lon = GeoService.city_coordinates(city)
        params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m"}
        async with self._session.get(self._base_url, params=params) as resp:
            data = await resp.json()
            return data["hourly"]["temperature_2m"][0]

async def main():
    # This will immediately initialize WeatherService and its dependencies,
    # because we have attempted to access the _session property.
    print(f"Is session closed: {WeatherService._session.closed}")

    # Subsequent calls do not reinitialize the provider.
    london = await WeatherService.temperature('London')
    new_york = await WeatherService.temperature('New York')
    print(f"London: {london:.2f}°C")
    print(f"New York: {new_york:.2f}°C")

    # Release the resources. Normally, this would be implemented in the
    # provider_dispose() method of the provider, but the async client must be closed
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
London: 13.10°C
New York: 11.30°C
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

from init_provider import BaseProvider, requires, setup

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
    #   of provider_init() will cause the provider to be initialized.
    db_path: str

    # ↓ Initialize, just like in a dataclass. But you NEVER
    #   have to create an instance of a provider manually.
    def provider_init(self) -> None:
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
    def provider_dispose(self):
        os.unlink(self.db_path)

    # ↓ Any call to the `conn` method will cause the
    #   provider to be initialized, if not already done.
    @contextmanager
    def conn(self) -> Generator[sqlite3.Connection, None, None]:
        """One-time connection to the database."""
        with sqlite3.connect(self.db_path) as conn:
            yield conn

# ↓ This one depends on another provider.
@requires(DatabaseService)
class UserService(BaseProvider):
    """Intenal API class to abstract the Users data layer."""

    # → Notice: NO provider_init() method here! Because there is nothing
    #   to initialize inside this specific provider itself.

    # ↓ Require initialization of all dependencies when this
    #   method is called.
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

## License

Licensed under the [Apache-2.0 License](./LICENSE).

[1]: https://docs.aiohttp.org/
[2]: https://martinfowler.com/eaaCatalog/repository.html