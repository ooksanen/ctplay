"""The one exception playbuild raises for anything the user must fix, and the TOML reading every loader shares."""
import tomllib
from contextlib import contextmanager
from pathlib import Path


class BuildError(Exception):
    """A reason the build must not produce an image. The message says what to fix."""


def load_toml(path: Path) -> dict:
    """A TOML file, or a BuildError naming the file and the line of a syntax error."""
    try:
        return tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise BuildError(f"{path}: {e}") from None


@contextmanager
def missing_keys(where: str):
    """A required key missing from a TOML table (t["addr"]) as a BuildError: "<where>: missing key 'addr'"."""
    try:
        yield
    except KeyError as e:
        raise BuildError(f"{where}: missing key {e}") from None
