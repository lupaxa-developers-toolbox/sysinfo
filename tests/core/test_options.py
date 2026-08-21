"""Tests for CollectOptions / profile resolution."""

from __future__ import annotations

import pytest

from lupaxa.sysinfo.options import (
    CollectOptions,
    apply_profile_to_collect,
    collect_options_to_aggregate_opts,
)


def test_cpu_memory_only() -> None:
    """Only the explicitly requested sections are enabled."""
    opts = CollectOptions(cpu=True, memory=True)
    agg = collect_options_to_aggregate_opts(opts)
    assert agg["cpu"] is True
    assert agg["memory"] is True
    assert agg["network"] is False
    assert agg["env"] is False


def test_all_does_not_enable_env() -> None:
    """``all=True`` enables every section apart from the environment dump."""
    opts = CollectOptions(all=True)
    agg = collect_options_to_aggregate_opts(opts)
    assert agg["cpu"] is True
    assert agg["env"] is False


def test_support_profile_sets_all_but_not_env() -> None:
    """The support profile enables everything but the environment, and full packages."""
    opts = apply_profile_to_collect(CollectOptions(profile="support"))
    agg = collect_options_to_aggregate_opts(opts)
    assert agg["cpu"] is True
    assert agg["env"] is False
    assert opts.packages_mode == "full"


def test_invalid_profile_raises() -> None:
    """An unknown profile name raises ``ValueError``."""
    with pytest.raises(ValueError, match="(?i)profile"):
        apply_profile_to_collect(CollectOptions(profile="nope"))
