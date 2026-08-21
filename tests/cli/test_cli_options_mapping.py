"""Tests for argparse-to-library options mapping."""

from __future__ import annotations

from lupaxa.sysinfo.cli import (
    build_parser,
    namespace_to_collect_options,
    namespace_to_redact_options,
)


def test_cpu_flag_maps() -> None:
    """``--cpu`` enables the CPU section in the library options."""
    args = build_parser().parse_args(["--cpu"])
    opts = namespace_to_collect_options(args)
    assert opts.cpu is True


def test_no_redact_flags_means_redact_disabled() -> None:
    """Redaction stays off when no redaction flag is supplied."""
    args = build_parser().parse_args([])
    redact = namespace_to_redact_options(args)
    assert redact.enabled is False


def test_redact_all_enables() -> None:
    """``--redact-all`` turns on every redaction category."""
    args = build_parser().parse_args(["--redact-all"])
    redact = namespace_to_redact_options(args)
    assert redact.enabled is True
    assert redact.hosts is True
