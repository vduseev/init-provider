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
- [License](#license)

## Quick start

Below is a full runnable example that uses everything in this library.

```python
{% include "full_example.py" %}
```

Output:

```shell
$ uv run python examples/full_example.py
{% include 'full_example.log' %}
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
{% include 'weather_service.py' %}
```

Output:

```shell
$ uv run python examples/weather_service.py
{% include 'weather_service.log' %}
```

### User service 

```python
{% include 'user_service.py' %}
```

Output:

```shell
$ uv run python examples/user_service.py
{% include 'user_service.log' %}
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
