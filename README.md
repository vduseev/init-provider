<h1><code>init-provider</code></h1>

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/init-provider)
![PyPI - Status](https://img.shields.io/pypi/status/init-provider)
![PyPI - License](https://img.shields.io/pypi/l/init-provider)

Lazy just-in-time dependency-aware initialization and instance provider.
Async and thread-safe, with minimal overhead.

> Imagine a dataclass but there is only one instance of it.
> And it can depend on other providers. And you can directly
> access all of its methods and fields without creating an instance
> without having to initialize it first.
> Provider will take care of it for you.

Table of Contents:

- [Quick start example](#quick-start-example)
- [Installation](#installation)

# Quick start example

The example below can run as-is.

```python
import logging
import warnings
import sqlite3
from contextlib import contextmanager
from typing import Generator

from init_provider import BaseProvider, requires, setup, init

# (Optional) Declare a setup function to do any one-time
# configuration by decorating it with the @setup decorator.
# This function will be called *exactly* once at the start of
# the application, when the **first call to any provider** is made.
@setup
def configure():
    log_format = "%(levelname)-8s %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=log_format)
    warnings.filterwarnings("ignore", module="some_module")

# ↓ Basic provider. Exposes 1 attribute: connection 
class DatabaseService(BaseProvider):
    """Single instance of connection ot SQLite."""

    # ↓ Any attempt to access a provider attribute outside
    #   of __init__ will cause the provider to be initialized.
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

    # → Notice: NO __init__ method here! Because there is nothing
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

If you close the project and run this example, you will see the same output:

```shell
$ uv run python examples/basic.py
INFO     Setup hook executed successfully.
DEBUG    About to initialize provider DatabaseService because of: db_path
DEBUG    Initialization order for provider DatabaseService is: DatabaseService
DEBUG    Initializing provider DatabaseService...
INFO     Provider DatabaseService initialized successfully
DEBUG    About to initialize provider UserService because of: get_name
DEBUG    Initialization order for provider UserService is: DatabaseService (initialized), UserService
DEBUG    Initializing provider UserService...
INFO     Provider UserService initialized successfully
>> database.db
>> Alice
>> Bob
```

# Installation

The package is available on PyPI. It has no dependencies and is implemented
in pure Python. Compatible with Python 3.10 and higher.

```bash
# Using pip
pip install init-provider

# Using uv
uv add init-provider
```