"""Tests for aggregate report meta and optional section wiring."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from lupaxa.sysinfo import collectors
from lupaxa.sysinfo.version import get_version


def _opts(**enabled: bool) -> dict[str, Any]:
    """Build an aggregate options mapping with only ``enabled`` sections on."""
    keys = [
        "cpu",
        "memory",
        "disks",
        "network",
        "listening_ports",
        "processes",
        "firewall",
        "runtimes",
        "gpu",
        "packages",
        "services",
        "hosts_dns",
        "logs",
        "storage",
        "hardware_extra",
        "pkg_layout",
        "env",
    ]
    base: dict[str, Any] = dict.fromkeys(keys, False)
    base.update(enabled)
    base["packages_mode"] = "fast"
    base["brew_taps"] = []
    base["firewall_prefer"] = "auto"
    return base


def test_aggregate_includes_schema_and_tool_version() -> None:
    """Every report carries the schema version, tool version, and basic section."""
    with patch.object(collectors, "basic_info", return_value={"hostname": "x"}):
        data = collectors.aggregate(_opts())
    assert data["schema_version"] == 1
    assert data["tool_version"] == get_version()
    assert data["basic"] == {"hostname": "x"}


def test_aggregate_calls_env_only_when_requested() -> None:
    """The environment collector runs only when its option is enabled."""
    with (
        patch.object(collectors, "basic_info", return_value={}),
        patch.object(collectors, "env_and_misc", return_value={"ENV": "1"}) as env_mock,
    ):
        data = collectors.aggregate(_opts(env=False))
        env_mock.assert_not_called()
        assert "env" not in data

        data = collectors.aggregate(_opts(env=True))
        env_mock.assert_called_once()
        assert data["env"] == {"ENV": "1"}


def test_aggregate_wires_services_when_enabled() -> None:
    """The services collector result is attached under the ``services`` key."""
    with (
        patch.object(collectors, "basic_info", return_value={}),
        patch.object(
            collectors, "services_and_startup", return_value={"ok": True}
        ) as services_mock,
    ):
        data = collectors.aggregate(_opts(services=True))
        services_mock.assert_called_once()
        assert data["services"] == {"ok": True}
