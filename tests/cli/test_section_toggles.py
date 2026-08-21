"""Tests for CLI section toggle resolution."""

from __future__ import annotations

from lupaxa.sysinfo.cli import build_parser, resolve_section_opts


def test_all_enables_new_sections_but_not_env() -> None:
    """``--all`` enables every section except the environment dump."""
    args = build_parser().parse_args(["--all"])
    opts = resolve_section_opts(args)
    assert opts["services"] is True
    assert opts["hosts_dns"] is True
    assert opts["logs"] is True
    assert opts["storage"] is True
    assert opts["hardware_extra"] is True
    assert opts["pkg_layout"] is True
    assert opts["env"] is False


def test_env_requires_explicit_flag() -> None:
    """The environment section is only collected when ``--env`` is given."""
    args = build_parser().parse_args(["--env"])
    opts = resolve_section_opts(args)
    assert opts["env"] is True


def test_all_with_no_services() -> None:
    """An explicit ``--no-services`` overrides ``--all``."""
    args = build_parser().parse_args(["--all", "--no-services"])
    opts = resolve_section_opts(args)
    assert opts["services"] is False


def test_support_profile_does_not_enable_env() -> None:
    """The support profile sets ``--all`` but still leaves the environment off."""
    args = build_parser().parse_args(["--profile", "support"])
    # apply profile the same way main does
    from lupaxa.sysinfo.cli import apply_profile

    apply_profile(args)
    opts = resolve_section_opts(args)
    assert args.all is True
    assert opts["env"] is False
