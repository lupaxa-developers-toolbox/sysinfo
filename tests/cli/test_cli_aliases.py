"""Tests for redaction CLI aliases."""

from __future__ import annotations

from lupaxa.sysinfo.cli import build_parser, normalize_redact_aliases


def test_no_redact_domain_aliases_map() -> None:
    """Legacy singular ``--no-redact-*`` flags set their canonical plural names."""
    args = build_parser().parse_args(
        ["--no-redact-domain", "--no-redact-domain-tree", "--no-redact-subdomain"]
    )
    normalize_redact_aliases(args)
    assert args.no_redact_domains is True
    assert args.no_redact_domain_trees is True
    assert args.no_redact_subdomains is True
