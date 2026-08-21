"""Redaction helpers for sysinfo reports."""

from __future__ import annotations

import contextlib
import os
import re
import sys
from collections.abc import Iterable, Sequence
from typing import Any, cast

# Public Suffix handling (tldextract, offline snapshot)
TLD_EXTRACT = None
try:
    import tldextract  # type: ignore

    # Use bundled snapshot; no network fetch
    TLD_EXTRACT = tldextract.TLDExtract(suffix_list_urls=())
except Exception:
    TLD_EXTRACT = None


def public_suffix_available() -> bool:
    """Return whether Public Suffix List aware domain handling can be used."""
    return TLD_EXTRACT is not None


# Placeholders
PH_FQDN = "<REDACTED FQDN>"
PH_HOSTNAME = "<REDACTED HOSTNAME>"
PH_USER = "<REDACTED USER>"
PH_HOME = "<REDACTED HOME>"
PH_WINHOME = "<REDACTED WINHOME>"
PH_EMAIL = "<REDACTED EMAIL>"
PH_IPV4 = "<REDACTED IPV4>"
PH_IPV6 = "<REDACTED IPV6>"
PH_MAC = "<REDACTED MAC>"
PH_SECRET = "<REDACTED SECRET>"  # noqa: S105 - replacement placeholder, not a credential
PH_CUSTOM = "<REDACTED CUSTOM>"
PH_DOMAIN = "<REDACTED DOMAIN>"

_IPv4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPv6_RE = re.compile(r"\b(?:(?:[A-Fa-f0-9]{1,4}:){1,7}[A-Fa-f0-9]{0,4})\b")
_MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
_EMAIL_RE = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")
_POSIX_HOME_RE = re.compile(r"(?:(?:/Users|/home)/)[^/\s]+")
_WIN_HOME_RE = re.compile(r"[A-Za-z]:\\\\Users\\\\[^\\\s]+")

DEFAULT_SECRET_KEYS = (
    "KEY",
    "SECRET",
    "TOKEN",
    "PASS",
    "PWD",
    "COOKIE",
    "AUTH",
    "CREDENTIAL",
    "BEARER",
)


def _registered_domain(domain: str) -> str | None:
    """Return registered domain (sld+suffix) using tldextract if available; else None."""
    if not domain:
        return None
    if TLD_EXTRACT:
        try:
            ext = TLD_EXTRACT(domain.strip("."))
            if ext.domain and ext.suffix:
                return f"{ext.domain}.{ext.suffix}".lower()
        except Exception:
            return None
    return None


def _domain_tree_list_simple(domain: str) -> list[str]:
    """Fallback: domain + parents until one label remains."""
    parts = [p for p in domain.strip(".").lower().split(".") if p]
    out: list[str] = []
    while len(parts) >= 2:
        out.append(".".join(parts))
        parts = parts[1:]
    return out


def _domain_tree_list_psl(domain: str) -> list[str]:
    """PSL-aware: include domain, walk parents up to the registered domain, stop there."""
    reg = _registered_domain(domain)
    parts = [p for p in domain.strip(".").lower().split(".") if p]
    out: list[str] = []
    while len(parts) >= 2:
        cand = ".".join(parts)
        out.append(cand)
        if reg and cand == reg:
            break
        parts = parts[1:]
    return out


def _build_redact_context(
    data_basic: dict[str, Any] | None,
    extra: dict[str, Any],
    enable: dict[str, bool],
    psl_aware: bool = False,
) -> dict[str, Any]:
    """Assemble the lookup tables ``_redact_string`` uses for a single run."""
    ctx: dict[str, Any] = {
        "enable": enable,
        "psl_aware": bool(psl_aware),
        "hostname": (data_basic or {}).get("hostname") or "",
        "fqdn": (data_basic or {}).get("fqdn") or "",
        "users": set(),
        "hosts_extra": set(extra.get("hosts", [])),
        "fqdns_extra": set(extra.get("fqdns", [])),
        "domains_extra": set(extra.get("domains", [])),
        "domain_trees_extra": set(),  # expanded tree entries
        "subdomains_extra": {d.lower() for d in extra.get("subdomains", [])},
        "homes_extra": set(extra.get("homes", [])),
        "winhomes_extra": set(extra.get("winhomes", [])),
        "emails_extra": set(extra.get("emails", [])),
        "ipv4_extra": set(extra.get("ipv4", [])),
        "ipv6_extra": set(extra.get("ipv6", [])),
        "macs_extra": set(extra.get("macs", [])),
        "secret_keys_extra": set(extra.get("secret_keys", [])),
        "custom_patterns": extra.get("custom_patterns", []),
        "secret_key_signals": set(DEFAULT_SECRET_KEYS),
    }
    # auto usernames
    for env_key in ("USER", "USERNAME", "LOGNAME"):
        if os.environ.get(env_key):
            ctx["users"].add(os.environ[env_key])
    for u in extra.get("users", []):
        if u:
            ctx["users"].add(u)

    # domains: derive base from FQDN
    if enable.get("domains"):
        fqdn = (ctx.get("fqdn") or "").lower()
        base = None
        if psl_aware and TLD_EXTRACT:
            rd = _registered_domain(fqdn)
            base = rd
        if not base and fqdn and "." in fqdn:
            base = fqdn.split(".", 1)[1]
        if base:
            ctx["domains_extra"].add(base)

    # domain-trees: expand provided items
    if enable.get("domain_trees"):
        expand = _domain_tree_list_psl if (psl_aware and TLD_EXTRACT) else _domain_tree_list_simple
        for d in extra.get("domain_trees", []) or []:
            for item in expand(d):
                ctx["domain_trees_extra"].add(item.lower())

    return ctx


def _apply_explicit_list(
    s: str, items: Iterable[str] | None, placeholder: str, word_boundary: bool = False
) -> str:
    """Replace each literal value in ``items`` with ``placeholder``."""
    for val in list(items or []):
        if not val:
            continue
        if word_boundary:
            s = re.sub(rf"\b{re.escape(val)}\b", placeholder, s)
        else:
            s = re.sub(re.escape(val), placeholder, s, flags=re.IGNORECASE)
    return s


def _redact_domains_suffix(s: str, domains: Iterable[str] | None, placeholder: str) -> str:
    """Replace each domain suffix in ``domains`` with ``placeholder``."""
    for dom in list(domains or []):
        d = dom.lower()
        s = re.sub(re.escape(d), placeholder, s, flags=re.IGNORECASE)
    return s


def _redact_subdomains(s: str, base_domains: Iterable[str] | None) -> str:
    """Redact subdomains of provided base domains.

    A match requires at least one leading label.
    """
    for dom in list(base_domains or []):
        d = re.escape(dom)
        pattern = rf"\b(?:[A-Za-z0-9-]+\.)+{d}\b"
        s = re.sub(pattern, PH_FQDN, s, flags=re.IGNORECASE)
    return s


def _redact_string(s: object, ctx: dict[str, Any]) -> object:
    """Apply every enabled redaction category to ``s``, leaving non-strings untouched."""
    if not isinstance(s, str):
        return s
    en = ctx["enable"]

    # Subdomains first (full FQDNs that are subdomains of given bases)
    if en.get("subdomains"):
        s = _redact_subdomains(s, ctx.get("subdomains_extra"))

    # Domains and domain-trees (suffix parts)
    if en.get("domains"):
        s = _redact_domains_suffix(s, ctx.get("domains_extra"), PH_DOMAIN)
    if en.get("domain_trees"):
        s = _redact_domains_suffix(s, ctx.get("domain_trees_extra"), PH_DOMAIN)

    # FQDNs
    if en["fqdns"]:
        if ctx.get("fqdn"):
            s = re.sub(re.escape(ctx["fqdn"]), PH_FQDN, s, flags=re.IGNORECASE)
        s = _apply_explicit_list(s, ctx.get("fqdns_extra"), PH_FQDN)

    # Hostnames
    if en["hosts"]:
        if ctx.get("hostname"):
            s = re.sub(rf"\b{re.escape(ctx['hostname'])}\b", PH_HOSTNAME, s, flags=re.IGNORECASE)
        s = _apply_explicit_list(s, ctx.get("hosts_extra"), PH_HOSTNAME)

    # Users
    if en["users"]:
        s = _apply_explicit_list(s, ctx.get("users"), PH_USER, word_boundary=True)

    # POSIX homes
    if en["homes"]:
        s = _POSIX_HOME_RE.sub(PH_HOME, s)
        s = _apply_explicit_list(s, ctx.get("homes_extra"), PH_HOME)

    # WIN homes
    if en["winhomes"]:
        s = _WIN_HOME_RE.sub(PH_WINHOME, s)
        s = _apply_explicit_list(s, ctx.get("winhomes_extra"), PH_WINHOME)

    # Emails
    if en["emails"]:
        s = _EMAIL_RE.sub(PH_EMAIL, s)
        s = _apply_explicit_list(s, ctx.get("emails_extra"), PH_EMAIL, word_boundary=True)

    # IPs/MACs
    if en["ipv4s"]:
        s = _IPv4_RE.sub(PH_IPV4, s)
        s = _apply_explicit_list(s, ctx.get("ipv4_extra"), PH_IPV4)
    if en["ipv6s"]:
        s = _IPv6_RE.sub(PH_IPV6, s)
        s = _apply_explicit_list(s, ctx.get("ipv6_extra"), PH_IPV6)
    if en["macs"]:
        s = _MAC_RE.sub(PH_MAC, s)
        s = _apply_explicit_list(s, ctx.get("macs_extra"), PH_MAC)

    # Custom
    if en["custom"]:
        for rx in ctx.get("custom_patterns", []):
            # Skip patterns that fail at substitution time (catastrophic backtracking, etc.).
            with contextlib.suppress(Exception):
                s = rx.sub(PH_CUSTOM, s)

    return s


def _redact_obj(obj: object, ctx: dict[str, Any]) -> object:
    """Walk ``obj`` recursively, redacting strings and masking secret-looking keys."""
    if obj is None:
        return None
    if isinstance(obj, str):
        return _redact_string(obj, ctx)
    if isinstance(obj, (int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_redact_obj(x, ctx) for x in obj]
    if isinstance(obj, dict):
        red: dict[Any, Any] = {}
        en = ctx["enable"]
        for k, v in obj.items():
            # Secret handling: if key name looks secret and secrets enabled, mask value entirely
            if en["secrets"] and isinstance(k, str):
                upperk = k.upper()
                if any(
                    sig in upperk
                    for sig in (ctx["secret_key_signals"] | set(ctx["secret_keys_extra"]))
                ):
                    red[k] = PH_SECRET
                    continue
            red[_redact_string(k, ctx) if isinstance(k, str) else k] = _redact_obj(v, ctx)
        return red
    return _redact_string(str(obj), ctx)


def _load_custom_patterns(
    paths: Sequence[str] | None, inline_patterns: Sequence[str] | None
) -> list[re.Pattern[str]]:
    """Compile inline regexes and pattern files, skipping any that fail to compile."""
    compiled: list[re.Pattern[str]] = []
    for pat in inline_patterns or []:
        try:
            compiled.append(re.compile(pat))
        except Exception as e:
            print(f"[redact] invalid --redact-rx pattern skipped: {pat} ({e})", file=sys.stderr)
    for path in paths or []:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        compiled.append(re.compile(line))
                    except Exception as e:
                        print(
                            f"[redact] invalid pattern in {path} skipped: {line} ({e})",
                            file=sys.stderr,
                        )
        except Exception as e:
            print(f"[redact] could not read {path}: {e}", file=sys.stderr)
    return compiled


def redact_data(
    data: dict[str, Any],
    enable: dict[str, bool],
    extra: dict[str, Any],
    custom_files: list[str] | None = None,
    custom_inline: list[str] | None = None,
    psl_aware: bool = False,
) -> dict[str, Any]:
    """Return a redacted copy of ``data`` for the enabled categories."""
    basic = data.get("basic", {})
    extra = dict(extra or {})
    extra["custom_patterns"] = _load_custom_patterns(custom_files, custom_inline)
    ctx = _build_redact_context(basic, extra, enable, psl_aware=psl_aware)
    return cast("dict[str, Any]", _redact_obj(data, ctx))
