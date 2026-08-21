"""Tests for redaction behaviour."""

from __future__ import annotations

from lupaxa.sysinfo.redact import redact_data


def _enable(**overrides: bool) -> dict[str, bool]:
    """Build a category enable map with everything off except ``overrides``."""
    base = {
        "fqdns": False,
        "hosts": False,
        "users": False,
        "homes": False,
        "winhomes": False,
        "emails": False,
        "ipv4s": False,
        "ipv6s": False,
        "macs": False,
        "secrets": False,
        "custom": False,
        "domains": False,
        "domain_trees": False,
        "subdomains": False,
    }
    base.update(overrides)
    return base


def test_emails_extra_ignored_when_emails_disabled() -> None:
    """Extra email entries are ignored while the email category is disabled."""
    data = {"basic": {}, "note": "contact admin@example.com please"}
    out = redact_data(
        data,
        enable=_enable(emails=False),
        extra={"emails": ["admin@example.com"]},
    )
    assert "admin@example.com" in out["note"]


def test_emails_extra_applied_when_emails_enabled() -> None:
    """Extra email entries are replaced once the email category is enabled."""
    data = {"basic": {}, "note": "contact admin@example.com please"}
    out = redact_data(
        data,
        enable=_enable(emails=True),
        extra={"emails": ["admin@example.com"]},
    )
    assert "admin@example.com" not in out["note"]
    assert "REDACTED" in out["note"]
