"""Tests for lupaxa.sysinfo.collect_report."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from lupaxa.sysinfo import collect_report, public_suffix_available
from lupaxa.sysinfo.options import CollectOptions


def test_returns_meta_and_basic() -> None:
    """A default report contains the schema version, tool version, and basics."""
    data = collect_report(collect=CollectOptions())
    assert data["schema_version"] == 1
    assert "tool_version" in data
    assert "basic" in data


def test_redacts_by_default(monkeypatch) -> None:
    """``collect_report`` redacts identifying values unless told otherwise."""
    sample = {
        "schema_version": 1,
        "tool_version": "0.0.0",
        "basic": {"hostname": "secret-host", "username": "tim"},
    }
    with patch("lupaxa.sysinfo.api.aggregate", return_value=sample):
        out = collect_report(collect=CollectOptions())
    assert out["basic"]["hostname"] != "secret-host"


def test_redact_false_keeps_raw() -> None:
    """``redact=False`` returns the collected values untouched."""
    sample = {
        "schema_version": 1,
        "tool_version": "0.0.0",
        "basic": {"hostname": "secret-host"},
    }
    with patch("lupaxa.sysinfo.api.aggregate", return_value=sample):
        out = collect_report(collect=CollectOptions(), redact=False)
    assert out["basic"]["hostname"] == "secret-host"


def test_section_kwargs_enable_cpu_only() -> None:
    """Section keyword arguments override individual ``CollectOptions`` fields."""
    with patch("lupaxa.sysinfo.api.aggregate") as agg:
        agg.return_value = {"schema_version": 1, "tool_version": "0.0.0", "basic": {}}
        collect_report(cpu=True, redact=False)
        passed = agg.call_args.args[0]
        assert passed["cpu"] is True
        assert passed["memory"] is False


def test_unknown_kwarg_raises_type_error() -> None:
    """An unrecognised keyword argument raises ``TypeError`` naming the field."""
    with pytest.raises(TypeError, match="cpuu"):
        collect_report(cpuu=True)


def test_unknown_kwarg_is_rejected_before_collection() -> None:
    """Bad keyword arguments are rejected before any collector runs."""
    with patch("lupaxa.sysinfo.api.aggregate") as agg, pytest.raises(TypeError):
        collect_report(collect=CollectOptions(), nonsense=1)
    agg.assert_not_called()


def test_default_redaction_is_public_suffix_aware_when_available() -> None:
    """Default redaction turns on PSL awareness when ``tldextract`` is installed."""
    sample = {"schema_version": 1, "tool_version": "0.0.0", "basic": {}}
    with (
        patch("lupaxa.sysinfo.api.aggregate", return_value=sample),
        patch("lupaxa.sysinfo.api.redact_data", return_value=sample) as redact,
    ):
        collect_report(collect=CollectOptions())
    assert redact.call_args.kwargs["psl_aware"] is public_suffix_available()


def test_redact_true_matches_default_redaction() -> None:
    """``redact=True`` behaves the same as the default redaction options."""
    sample = {"schema_version": 1, "tool_version": "0.0.0", "basic": {}}
    with (
        patch("lupaxa.sysinfo.api.aggregate", return_value=sample),
        patch("lupaxa.sysinfo.api.redact_data", return_value=sample) as redact,
    ):
        collect_report(collect=CollectOptions(), redact=True)
    assert redact.call_args.kwargs["psl_aware"] is public_suffix_available()


def test_json_serializable() -> None:
    """A full unredacted report can be serialised to JSON."""
    data = collect_report(collect=CollectOptions(), redact=False)
    json.dumps(data, default=str)
