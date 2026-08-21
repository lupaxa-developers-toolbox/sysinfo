"""Library modules stay free of CLI-only dependencies."""

from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "lupaxa" / "sysinfo"

LIBRARY_MODULES = frozenset(
    {
        "__init__.py",
        "api.py",
        "collectors.py",
        "options.py",
        "redact.py",
        "version.py",
    }
)

CLI_MODULES = frozenset(
    {
        "__main__.py",
        "cli.py",
        "export.py",
        "spinner.py",
    }
)

YAML_IMPORT = re.compile(
    r"^\s*(?:import\s+yaml|from\s+yaml\s+import)\b",
    re.MULTILINE,
)


def test_source_tree_contains_library_and_cli_modules() -> None:
    """The flat package ships library and CLI modules under one tree."""
    modules = sorted(path.name for path in SRC_ROOT.glob("*.py"))
    assert set(modules) >= LIBRARY_MODULES | CLI_MODULES
    assert "cli.py" in modules


def test_library_modules_do_not_import_pyyaml() -> None:
    """Library modules must not import PyYAML (CLI export owns YAML I/O)."""
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in sorted(SRC_ROOT.glob("*.py"))
        if path.name in LIBRARY_MODULES and YAML_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_cli_modules_do_not_import_pyyaml_except_export() -> None:
    """Only ``export.py`` among CLI modules may import PyYAML."""
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in sorted(SRC_ROOT.glob("*.py"))
        if path.name in CLI_MODULES
        and path.name != "export.py"
        and YAML_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
