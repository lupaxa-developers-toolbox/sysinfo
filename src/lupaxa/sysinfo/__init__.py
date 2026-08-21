"""Lupaxa sysinfo — cross-platform system inventory library."""

from __future__ import annotations

from .api import collect_report
from .collectors import SCHEMA_VERSION, set_strict_missing
from .options import CollectOptions, RedactOptions
from .redact import public_suffix_available
from .version import __version__, get_version

__all__ = [
    "SCHEMA_VERSION",
    "CollectOptions",
    "RedactOptions",
    "__version__",
    "collect_report",
    "get_version",
    "public_suffix_available",
    "set_strict_missing",
]
