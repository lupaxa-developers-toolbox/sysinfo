"""Installed CLI entry point smoke test."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from lupaxa.sysinfo import __version__
from lupaxa.sysinfo import cli as cli_mod
from lupaxa.sysinfo.cli import main


def test_cli_main_version(capsys: pytest.CaptureFixture[str]) -> None:
    """``--version`` prints the package version and exits zero."""
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out


def _installed_sysinfo_script() -> Path:
    """Return the installed ``sysinfo`` console script, skipping if absent."""
    if sys.platform == "win32":
        script = Path(sys.prefix) / "Scripts" / "sysinfo.exe"
    else:
        script = Path(sys.prefix) / "bin" / "sysinfo"
    if not script.is_file():
        pytest.skip("sysinfo console script not installed in this environment")
    return script


def test_sysinfo_console_script_version() -> None:
    """The installed console script reports the package version."""
    exe = _installed_sysinfo_script()
    proc = subprocess.run(  # noqa: S603 - path comes from this interpreter's own prefix
        [str(exe), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = (proc.stdout or "") + (proc.stderr or "")
    assert __version__ in out


def test_package_main_entry() -> None:
    """``python -m lupaxa.sysinfo`` reports the package version."""
    proc = subprocess.run(
        [sys.executable, "-m", "lupaxa.sysinfo", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = (proc.stdout or "") + (proc.stderr or "")
    assert __version__ in out


@pytest.mark.parametrize(
    ("option", "writer_name"),
    [
        ("--json", "save_json_file"),
        ("--yaml", "save_yaml_file"),
        ("--xml", "save_xml_file"),
        ("--html", "export_html"),
    ],
)
def test_cli_exits_nonzero_when_report_write_fails(
    monkeypatch: pytest.MonkeyPatch, option: str, writer_name: str
) -> None:
    """A failed report write makes the CLI exit with status 1."""
    monkeypatch.setattr(cli_mod, "collect_report", lambda **_kwargs: {"basic": {}})
    monkeypatch.setattr(cli_mod, writer_name, lambda _data, _path: False)

    with pytest.raises(SystemExit) as exc:
        main(["--no-spinner", option, "/unwritable/report"])

    assert exc.value.code == 1
