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
