"""aioasuswrt package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aioasuswrt")
except PackageNotFoundError:
    __version__ = "dev"
