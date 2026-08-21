"""Command-line interface for the sysinfo collector."""

from __future__ import annotations

import argparse
import contextlib
import signal
import sys
from types import FrameType
from typing import Any

from lupaxa.sysinfo import (
    CollectOptions,
    RedactOptions,
    collect_report,
    public_suffix_available,
    set_strict_missing,
)

from .export import (
    dumps_json,
    dumps_xml,
    dumps_yaml,
    export_html,
    pretty_print_summary,
    save_json_file,
    save_xml_file,
    save_yaml_file,
)
from .spinner import Spinner
from .version import __version__


def _set_true_if_unset(args: argparse.Namespace, on_attr: str, no_attr: str | None = None) -> None:
    if no_attr and getattr(args, no_attr, False):
        return
    if not getattr(args, on_attr, False):
        setattr(args, on_attr, True)


def apply_profile(args: argparse.Namespace) -> None:
    """Apply a named profile while preserving explicit disable flags."""
    profile = getattr(args, "profile", None)
    if profile == "minimal":
        args.no_spinner = True
    elif profile == "ci":
        for on_attr, no_attr in (
            ("cpu", "no_cpu"),
            ("memory", "no_memory"),
            ("disks", "no_disks"),
            ("network", "no_network"),
            ("runtimes", "no_runtimes"),
            ("packages", "no_packages"),
        ):
            _set_true_if_unset(args, on_attr, no_attr)
        args.no_spinner = True
        args.strict_missing = True
    elif profile == "support":
        args.all = True
        if args.packages_mode == "fast":
            args.packages_mode = "full"


def normalize_redact_aliases(args: argparse.Namespace) -> None:
    """Map legacy singular redaction disable flags to canonical names."""
    aliases = {
        "no_redact_domain": "no_redact_domains",
        "no_redact_domain_tree": "no_redact_domain_trees",
        "no_redact_subdomain": "no_redact_subdomains",
    }
    for alias, canonical in aliases.items():
        if getattr(args, alias, False):
            setattr(args, canonical, True)


def resolve_section_opts(args: argparse.Namespace) -> dict[str, Any]:
    """Resolve section enable/disable flags into collector options."""

    def resolve(on_flag: str, off_flag: str, *, include_in_all: bool = True) -> bool:
        enabled = bool(args.all) if include_in_all else False
        if getattr(args, on_flag, False):
            enabled = True
        if getattr(args, off_flag, False):
            enabled = False
        return enabled

    return {
        "cpu": resolve("cpu", "no_cpu"),
        "memory": resolve("memory", "no_memory"),
        "disks": resolve("disks", "no_disks"),
        "network": resolve("network", "no_network"),
        "listening_ports": resolve("listening_ports", "no_listening_ports"),
        "processes": resolve("processes", "no_processes"),
        "firewall": resolve("firewall", "no_firewall"),
        "runtimes": resolve("runtimes", "no_runtimes"),
        "gpu": resolve("gpu", "no_gpu"),
        "packages": resolve("packages", "no_packages"),
        "services": resolve("services", "no_services"),
        "hosts_dns": resolve("hosts_dns", "no_hosts_dns"),
        "logs": resolve("logs", "no_logs"),
        "storage": resolve("storage", "no_storage"),
        "hardware_extra": resolve("hardware_extra", "no_hardware_extra"),
        "pkg_layout": resolve("pkg_layout", "no_pkg_layout"),
        "env": resolve("env", "no_env", include_in_all=False),
        "packages_mode": args.packages_mode,
        "brew_taps": [tap.strip() for tap in args.brew_taps.split(",")] if args.brew_taps else [],
        "firewall_prefer": args.firewall_prefer,
    }


def namespace_to_collect_options(args: argparse.Namespace) -> CollectOptions:
    """Map resolved CLI collection flags to public library options.

    Call ``apply_profile(args)`` first: profiles are expanded into individual
    section flags on the namespace, and the returned options carry
    ``all=False`` so the library does not re-expand them.
    """
    return CollectOptions(all=False, **resolve_section_opts(args))


def build_parser() -> argparse.ArgumentParser:
    """Build the sysinfo command-line parser."""
    parser = argparse.ArgumentParser(
        description="Collect system info (cross-platform) — modular sections + granular redaction"
    )

    parser.add_argument(
        "--profile",
        choices=["minimal", "ci", "support"],
        help="Preset of sensible flags you can still override.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument(
        "--all", action="store_true", help="Enable all sections except basic and environment."
    )
    parser.add_argument("--cpu", action="store_true", help="Include CPU info.")
    parser.add_argument("--no-cpu", action="store_true", help="Disable CPU info.")
    parser.add_argument("--memory", action="store_true", help="Include memory info.")
    parser.add_argument("--no-memory", action="store_true", help="Disable memory info.")
    parser.add_argument("--disks", action="store_true", help="Include disk info.")
    parser.add_argument("--no-disks", action="store_true", help="Disable disk info.")
    parser.add_argument(
        "--network", action="store_true", help="Include network interfaces and routes."
    )
    parser.add_argument("--no-network", action="store_true", help="Disable network info.")
    parser.add_argument(
        "--listening-ports",
        dest="listening_ports",
        action="store_true",
        help="Include listening ports.",
    )
    parser.add_argument(
        "--no-listening-ports",
        dest="no_listening_ports",
        action="store_true",
        help="Disable listening ports.",
    )
    parser.add_argument("--processes", action="store_true", help="Include top processes by memory.")
    parser.add_argument("--no-processes", action="store_true", help="Disable processes section.")
    parser.add_argument("--firewall", action="store_true", help="Include firewall summary.")
    parser.add_argument("--no-firewall", action="store_true", help="Disable firewall summary.")
    parser.add_argument(
        "--firewall-prefer",
        choices=["auto", "nft", "iptables"],
        default="auto",
        help="Linux firewall preference.",
    )
    parser.add_argument(
        "--runtimes",
        action="store_true",
        help="Include installed runtimes (Java/.NET/Python/Ruby/Node).",
    )
    parser.add_argument("--no-runtimes", action="store_true", help="Disable runtimes.")
    parser.add_argument("--gpu", action="store_true", help="Include GPU/driver info.")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU info.")
    parser.add_argument(
        "--packages",
        action="store_true",
        help="Include system packages, per-user packages, and user RubyGems.",
    )
    parser.add_argument("--no-packages", action="store_true", help="Disable packages.")
    parser.add_argument(
        "--packages-mode",
        choices=["fast", "full"],
        default="fast",
        help="System package collection mode.",
    )
    parser.add_argument(
        "--brew-taps",
        metavar="CSV",
        help="Homebrew taps to include (e.g. homebrew/core,hashicorp/tap).",
    )

    parser.add_argument("--services", action="store_true", help="Include services / startup info.")
    parser.add_argument(
        "--no-services", action="store_true", help="Disable services / startup info."
    )
    parser.add_argument(
        "--hosts-dns", dest="hosts_dns", action="store_true", help="Include hosts and DNS info."
    )
    parser.add_argument(
        "--no-hosts-dns",
        dest="no_hosts_dns",
        action="store_true",
        help="Disable hosts and DNS info.",
    )
    parser.add_argument("--logs", action="store_true", help="Include logs overview.")
    parser.add_argument("--no-logs", action="store_true", help="Disable logs overview.")
    parser.add_argument("--storage", action="store_true", help="Include storage and mounts.")
    parser.add_argument("--no-storage", action="store_true", help="Disable storage and mounts.")
    parser.add_argument(
        "--hardware-extra",
        dest="hardware_extra",
        action="store_true",
        help="Include extra hardware probes.",
    )
    parser.add_argument(
        "--no-hardware-extra",
        dest="no_hardware_extra",
        action="store_true",
        help="Disable extra hardware probes.",
    )
    parser.add_argument(
        "--pkg-layout",
        dest="pkg_layout",
        action="store_true",
        help="Include package manager layout paths.",
    )
    parser.add_argument(
        "--no-pkg-layout",
        dest="no_pkg_layout",
        action="store_true",
        help="Disable package manager layout.",
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="Include environment variables (NOT included in --all).",
    )
    parser.add_argument("--no-env", action="store_true", help="Disable environment section.")

    parser.add_argument(
        "--output",
        choices=["json", "yaml", "xml", "summary", "both"],
        default="json",
        help="What to print to stdout.",
    )
    parser.add_argument("--json", metavar="PATH", help="Also save JSON to this file.")
    parser.add_argument("--yaml", metavar="PATH", help="Also save YAML to this file.")
    parser.add_argument("--xml", metavar="PATH", help="Also save XML to this file.")
    parser.add_argument("--html", metavar="PATH", help="Also save compact HTML to this file.")
    parser.add_argument("--no-spinner", action="store_true", help="Disable progress spinner.")
    parser.add_argument(
        "--strict-missing",
        action="store_true",
        help="Normalize missing tools to {'ok':false,'stderr':'not found'}.",
    )

    parser.add_argument(
        "--public-suffix-aware",
        action="store_true",
        help="Force PSL-aware domain logic ON (if tldextract is available).",
    )
    parser.add_argument(
        "--no-public-suffix-aware", action="store_true", help="Force PSL-aware domain logic OFF."
    )

    parser.add_argument(
        "--redact-all",
        action="store_true",
        help="Enable all redaction categories (including domain categories).",
    )
    parser.add_argument("--redact", action="store_true", help=argparse.SUPPRESS)
    for category in (
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
        "domain-trees",
        "subdomains",
    ):
        parser.add_argument(
            f"--redact-{category}", action="store_true", help=f"Enable redaction for {category}."
        )
        parser.add_argument(
            f"--no-redact-{category}",
            action="store_true",
            help=f"Disable redaction for {category}.",
        )
    parser.add_argument("--no-redact-domain", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-redact-domain-tree", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-redact-subdomain", action="store_true", help=argparse.SUPPRESS)

    parser.add_argument(
        "--redact-fqdn", action="append", default=[], help="Add FQDN to redact (repeatable)."
    )
    parser.add_argument(
        "--redact-host", action="append", default=[], help="Add hostname to redact (repeatable)."
    )
    parser.add_argument(
        "--redact-user", action="append", default=[], help="Add username to redact (repeatable)."
    )
    parser.add_argument(
        "--redact-home",
        action="append",
        default=[],
        help="Add POSIX home path to redact (repeatable).",
    )
    parser.add_argument(
        "--redact-winhome",
        action="append",
        default=[],
        help="Add Windows home path to redact (repeatable).",
    )
    parser.add_argument(
        "--redact-email", action="append", default=[], help="Add email to redact (repeatable)."
    )
    parser.add_argument(
        "--redact-ipv4",
        action="append",
        default=[],
        help="Add IPv4 address to redact (repeatable).",
    )
    parser.add_argument(
        "--redact-ipv6",
        action="append",
        default=[],
        help="Add IPv6 address to redact (repeatable).",
    )
    parser.add_argument(
        "--redact-mac", action="append", default=[], help="Add MAC address to redact (repeatable)."
    )
    parser.add_argument(
        "--redact-domain",
        action="append",
        default=[],
        help="Add domain suffix to redact (repeatable).",
    )
    parser.add_argument(
        "--redact-domain-tree",
        action="append",
        default=[],
        help="Add domain and its parents to redact (repeatable).",
    )
    parser.add_argument(
        "--redact-subdomain",
        action="append",
        default=[],
        help="Add base domain whose subdomains are redacted (repeatable).",
    )
    parser.add_argument(
        "--redact-secret-key",
        action="append",
        default=[],
        help="Additional environment variable names to treat as secrets.",
    )
    parser.add_argument(
        "--redact-rx", action="append", default=[], help="Custom regex to redact (repeatable)."
    )
    parser.add_argument(
        "--redact-file",
        action="append",
        default=[],
        help="File containing regexes to redact (repeatable).",
    )
    return parser


def _resolve_redaction(args: argparse.Namespace) -> tuple[dict[str, bool], dict[str, list[str]]]:
    all_on = bool(args.redact_all)

    def resolve(name: str) -> bool:
        enabled = all_on
        if getattr(args, f"redact_{name}", False):
            enabled = True
        if getattr(args, f"no_redact_{name}", False):
            enabled = False
        return enabled

    enable = {
        name: resolve(name)
        for name in (
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
    }
    extra = {
        "fqdns": args.redact_fqdn or [],
        "hosts": args.redact_host or [],
        "users": args.redact_user or [],
        "homes": args.redact_home or [],
        "winhomes": args.redact_winhome or [],
        "emails": args.redact_email or [],
        "ipv4": args.redact_ipv4 or [],
        "ipv6": args.redact_ipv6 or [],
        "macs": args.redact_mac or [],
        "domains": [domain.lower() for domain in (args.redact_domain or [])],
        "domain_trees": [domain.lower() for domain in (args.redact_domain_tree or [])],
        "subdomains": [domain.lower() for domain in (args.redact_subdomain or [])],
        "secret_keys": args.redact_secret_key or [],
    }
    return enable, extra


def namespace_to_redact_options(args: argparse.Namespace) -> RedactOptions:
    """Map CLI redaction flags to public library options."""
    enable, extra = _resolve_redaction(args)
    custom_files = list(args.redact_file or [])
    custom_inline = list(args.redact_rx or [])
    psl_aware = public_suffix_available() and not args.no_public_suffix_aware
    return RedactOptions(
        enabled=bool(any(enable.values()) or custom_files or custom_inline),
        **enable,
        extra=extra,
        custom_files=custom_files,
        custom_inline=custom_inline,
        psl_aware=psl_aware,
    )


def main(argv: list[str] | None = None) -> None:
    """Run the sysinfo command-line interface."""
    args = build_parser().parse_args(argv)
    apply_profile(args)
    set_strict_missing(bool(args.strict_missing))

    if args.redact and not args.redact_all:
        args.redact_all = True
        print("[notice] --redact is deprecated; use --redact-all", file=sys.stderr)
    normalize_redact_aliases(args)

    if args.public_suffix_aware and not public_suffix_available():
        print(
            "[notice] --public-suffix-aware requested but tldextract not available; falling back.",
            file=sys.stderr,
        )

    collect = namespace_to_collect_options(args)
    redact = namespace_to_redact_options(args)
    spinner = None
    if not args.no_spinner:
        spinner = Spinner("Collecting data — this may take a while...")

        def stop_spinner(_signum: int, _frame: FrameType | None) -> None:
            if spinner:
                spinner.stop()
            raise SystemExit(1)

        signal.signal(signal.SIGINT, stop_spinner)
        # SIGTERM is not available or not settable on some platforms (e.g. Windows).
        with contextlib.suppress(Exception):
            signal.signal(signal.SIGTERM, stop_spinner)
        spinner.start()

    try:
        data = collect_report(collect=collect, redact=redact)
    finally:
        if spinner:
            spinner.stop()

    if args.output in ("json", "both"):
        print(dumps_json(data))
    if args.output == "yaml":
        text = dumps_yaml(data)
        print(text, end="" if text.endswith("\n") else "\n")
    if args.output == "xml":
        text = dumps_xml(data)
        print(text, end="" if text.endswith("\n") else "\n")
    if args.output in ("summary", "both"):
        print("\n\n========== HUMAN SUMMARY ==========\n")
        pretty_print_summary(data)

    write_failed = False
    if args.json:
        if save_json_file(data, args.json):
            print(f"\n[OK] JSON saved to: {args.json}", file=sys.stderr)
        else:
            write_failed = True
    if args.yaml:
        if save_yaml_file(data, args.yaml):
            print(f"\n[OK] YAML saved to: {args.yaml}", file=sys.stderr)
        else:
            write_failed = True
    if args.xml:
        if save_xml_file(data, args.xml):
            print(f"\n[OK] XML saved to: {args.xml}", file=sys.stderr)
        else:
            write_failed = True
    if args.html:
        if export_html(data, args.html):
            print(f"\n[OK] HTML report saved to: {args.html}", file=sys.stderr)
        else:
            write_failed = True
    if write_failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
