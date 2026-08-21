"""CLI modules may only depend on the public ``lupaxa.sysinfo`` API."""

from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "lupaxa" / "sysinfo"

CLI_MODULES = (
    SRC_ROOT / "cli.py",
    SRC_ROOT / "export.py",
    SRC_ROOT / "spinner.py",
    SRC_ROOT / "__main__.py",
)

FORBIDDEN = re.compile(
    r"from\s+lupaxa\.sysinfo\.(?:collectors|redact)\s+import"
    r"|import\s+lupaxa\.sysinfo\.(?:collectors|redact)"
    r"|from\s+lupaxa\.sysinfo\s+import\s+[^\n]*\b(?:collectors|redact)\b"
)


def test_cli_source_modules_exist() -> None:
    """The CLI modules are present under the flat package tree."""
    missing = [str(path.relative_to(REPO_ROOT)) for path in CLI_MODULES if not path.is_file()]
    assert missing == []


def test_cli_does_not_import_private_core_modules() -> None:
    """No CLI module reaches into ``collectors`` or ``redact`` directly."""
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in CLI_MODULES
        if FORBIDDEN.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
