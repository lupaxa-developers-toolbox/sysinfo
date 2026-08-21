"""Library-facing collection and redaction option types."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

SECTION_NAMES: tuple[str, ...] = (
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
)

_CI_SECTIONS: tuple[str, ...] = (
    "cpu",
    "memory",
    "disks",
    "network",
    "runtimes",
    "packages",
)

_REDACT_CATEGORY_NAMES: tuple[str, ...] = (
    "fqdns",
    "hosts",
    "users",
    "homes",
    "winhomes",
    "emails",
    "ipv4s",
    "ipv6s",
    "macs",
    "secrets",
    "custom",
    "domains",
    "domain_trees",
    "subdomains",
)


@dataclass
class CollectOptions:
    """Options controlling which report sections are collected."""

    profile: str | None = None
    all: bool = False
    cpu: bool = False
    memory: bool = False
    disks: bool = False
    network: bool = False
    listening_ports: bool = False
    processes: bool = False
    firewall: bool = False
    runtimes: bool = False
    gpu: bool = False
    packages: bool = False
    services: bool = False
    hosts_dns: bool = False
    logs: bool = False
    storage: bool = False
    hardware_extra: bool = False
    pkg_layout: bool = False
    env: bool = False
    packages_mode: str = "fast"
    brew_taps: list[str] = field(default_factory=list)
    firewall_prefer: str | None = "auto"


@dataclass
class RedactOptions:
    """Options controlling report redaction behaviour."""

    enabled: bool = True
    fqdns: bool = True
    hosts: bool = True
    users: bool = True
    homes: bool = True
    winhomes: bool = True
    emails: bool = True
    ipv4s: bool = True
    ipv6s: bool = True
    macs: bool = True
    secrets: bool = True
    custom: bool = True
    domains: bool = True
    domain_trees: bool = True
    subdomains: bool = True
    extra: dict[str, list[str]] = field(default_factory=dict)
    custom_files: list[str] = field(default_factory=list)
    custom_inline: list[str] = field(default_factory=list)
    psl_aware: bool = False

    def as_enable_map(self) -> dict[str, bool]:
        """Return the category enable map expected by ``redact_data``."""
        return {name: bool(getattr(self, name)) for name in _REDACT_CATEGORY_NAMES}


def apply_profile_to_collect(opts: CollectOptions) -> CollectOptions:
    """Apply a named collection profile, mirroring CLI ``apply_profile`` semantics."""
    profile = opts.profile
    if profile is None or profile == "minimal":
        return opts
    if profile == "ci":
        updates: dict[str, Any] = {name: True for name in _CI_SECTIONS if not getattr(opts, name)}
        return replace(opts, **updates)
    if profile == "support":
        packages_mode = opts.packages_mode
        if packages_mode == "fast":
            packages_mode = "full"
        return replace(opts, all=True, packages_mode=packages_mode)
    raise ValueError(f"Unknown profile: {profile!r}")


def collect_options_to_aggregate_opts(opts: CollectOptions) -> dict[str, Any]:
    """Resolve section enable flags into collector aggregate options."""
    result: dict[str, Any] = {}
    for name in SECTION_NAMES:
        include_in_all = name != "env"
        enabled = bool(getattr(opts, name))
        if not enabled and include_in_all and opts.all:
            enabled = True
        result[name] = enabled
    result["packages_mode"] = opts.packages_mode
    result["brew_taps"] = list(opts.brew_taps)
    result["firewall_prefer"] = opts.firewall_prefer
    return result
