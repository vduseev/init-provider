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
