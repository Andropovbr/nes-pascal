"""Minimal NES Pascal compiler."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nes-pascal")
except PackageNotFoundError:
    __version__ = "0.5.8"
