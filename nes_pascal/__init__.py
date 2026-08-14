"""Minimal NES Pascal compiler."""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib

_PACKAGE_NAME = "nes-pascal"


def _version_from_source_tree() -> str:
    """Read the version from pyproject.toml when running from the source tree.

    The installed package reports its version through importlib.metadata. When
    that metadata is unavailable (for example, running python -m nes_pascal.cli
    from a checkout that was never installed), pyproject.toml remains the sole
    authoritative version source.
    """

    project_root = Path(__file__).resolve().parent.parent
    pyproject_path = project_root / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as handle:
            data = tomllib.load(handle)
        return data["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "0.0.0"


try:
    __version__ = version(_PACKAGE_NAME)
except PackageNotFoundError:
    __version__ = _version_from_source_tree()
