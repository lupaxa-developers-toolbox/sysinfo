"""JSON, YAML, HTML, XML, and summary exporters for sysinfo reports."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from html import escape
from typing import Any

import yaml

_INVALID_XML_NAME = re.compile(r"[^\w.\-]", re.UNICODE)


def _is_xml_1_0_char(codepoint: int) -> bool:
    """Return whether *codepoint* is allowed by the XML 1.0 Char production.

    Collector output can contain terminal escapes and NULs that would otherwise
    produce ill-formed documents; those codepoints are rejected here.
    """
    return (
        codepoint in (0x9, 0xA, 0xD)
        or 0x20 <= codepoint <= 0xD7FF
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )


def _sanitize_xml_text(text: str) -> str:
    """Drop characters outside the XML 1.0 Char production."""
    return "".join(ch for ch in text if _is_xml_1_0_char(ord(ch)))


def pretty_print_summary(data: dict[str, Any]) -> None:
    """Print a human-readable digest of the report to stdout."""

    def dump(title: str, obj: object) -> None:
        print(f"\n=== {title} ===")
        print(json.dumps(obj, indent=2, default=str))

    if "basic" in data:
        dump("Basic", data["basic"])
    if "cpu" in data and data["cpu"] is not None:
        dump("CPU", data["cpu"])
    if "memory" in data and data["memory"] is not None:
        dump("Memory", data["memory"])
    if "disks" in data and data["disks"] is not None:
        print("\n=== Disks (partitions) ===")
        for partition in data["disks"].get("partitions", []):
            print(f"{partition['device']} -> {partition['mountpoint']} ({partition['fstype']})")
            if partition.get("usage"):
                print("  usage:", partition["usage"])
    if "network" in data and data["network"] is not None:
        dump(
            "Network (interfaces/routes)",
            {
                "interfaces": data["network"].get("interfaces"),
                "route": data["network"].get("route"),
            },
        )
    if "listening_ports" in data and data["listening_ports"] is not None:
        print("\n=== Listening Ports ===")
        lp = data["listening_ports"]
        if isinstance(lp, list):
            for port in lp[:30]:
                print(" ", port)
        else:
            print(lp)
    if "processes_top" in data and data["processes_top"] is not None:
        print("\n=== Top Processes by memory ===")
        for process in data["processes_top"][:30]:
            print(" ", process)
    if "firewall" in data and data["firewall"] is not None:
        print("\n=== Firewall (summary) ===")
        fw = data["firewall"]
        if isinstance(fw, dict):
            if "preference" in fw:
                print(" preference:", fw.get("preference"))
            for key in ("nft_ruleset", "iptables_filter", "pf_rules", "netsh"):
                if key in fw:
                    sub = fw[key]
                    ok = sub.get("ok", True) if isinstance(sub, dict) else True
                    print(f"  {key}: {'ok' if ok else 'error'}")
        else:
            print(fw)
    if "runtimes" in data and data["runtimes"] is not None:
        dump("Runtimes", data["runtimes"])
    if "gpu" in data and data["gpu"] is not None:
        dump("GPU", data["gpu"])
    if "packages" in data and data["packages"] is not None:
        dump("System Packages (keys)", sorted(data["packages"].keys()))
    if "user_packages" in data and data["user_packages"] is not None:
        dump("User Packages (keys)", sorted(data["user_packages"].keys()))
    if "user_rubygems" in data and data["user_rubygems"] is not None:
        dump("User RubyGems (keys)", sorted(data["user_rubygems"].keys()))
    for key, title in (
        ("services", "Services"),
        ("hosts_dns", "Hosts and DNS"),
        ("logs", "Logs"),
        ("storage", "Storage"),
        ("hardware_extra", "Additional Hardware"),
        ("package_managers_layout", "Package Manager Layout"),
        ("env", "Environment"),
    ):
        if key in data and data[key] is not None:
            dump(title, data[key])


def html_section(title: str, content_html: str) -> str:
    """Wrap pre-rendered HTML in a titled report section."""
    return f"""
<section style="margin-bottom:1.2rem;">
  <h2 style="font:600 16px/1.4 system-ui, -apple-system, Segoe UI, Roboto,
             Helvetica, Arial;">{escape(title)}</h2>
  <div style="font:400 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas,
              monospace; white-space:pre-wrap; background:#fafafa;
              border:1px solid #eee; border-radius:8px; padding:10px;">
    {content_html}
  </div>
</section>
"""


def export_html(data: dict[str, Any], path: str) -> bool:
    """Write a standalone HTML report to ``path``; return whether it succeeded."""

    def json_html(obj: object) -> str:
        return escape(json.dumps(obj, indent=2, default=str))

    sections: list[str] = []
    for key, title in [
        ("basic", "Basic"),
        ("cpu", "CPU"),
        ("memory", "Memory"),
        ("disks", "Disks"),
        ("network", "Network"),
        ("listening_ports", "Listening Ports"),
        ("processes_top", "Top Processes (by memory)"),
        ("firewall", "Firewall"),
        ("runtimes", "Runtimes"),
        ("gpu", "GPU"),
        ("packages", "System Packages"),
        ("user_packages", "User Packages"),
        ("user_rubygems", "User RubyGems"),
        ("brew_tap_formulas", "Homebrew (selected taps)"),
        ("services", "Services"),
        ("hosts_dns", "Hosts and DNS"),
        ("logs", "Logs"),
        ("storage", "Storage"),
        ("hardware_extra", "Additional Hardware"),
        ("package_managers_layout", "Package Manager Layout"),
        ("env", "Environment"),
    ]:
        if key in data and data[key] is not None:
            sections.append(html_section(title, f"<pre>{json_html(data[key])}</pre>"))

    full_json = json_html(data)
    sections.append(
        f"""
<details>
  <summary style="cursor:pointer; font:600 14px/1.4 system-ui;">Full JSON (expand)</summary>
  <pre style="margin-top:8px; font:400 12px/1.45 ui-monospace;">{full_json}</pre>
</details>
"""
    )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>System Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:24px; color:#111; background:#fff;">
  <h1 style="font:700 20px/1.3 system-ui;">System Report</h1>
  {"".join(sections)}
</body></html>"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return True
    except Exception as e:
        print(f"Failed to write HTML: {e}", file=sys.stderr)
        return False


def dumps_json(data: dict[str, Any]) -> str:
    """Serialise the report as indented JSON."""
    return json.dumps(data, indent=2)


def dumps_yaml(data: dict[str, Any]) -> str:
    """Serialise the report as YAML, coercing unsupported values to strings."""
    compatible = json.loads(json.dumps(data, default=str))
    return yaml.safe_dump(compatible, sort_keys=False, allow_unicode=True)


def save_json_file(data: dict[str, Any], filename: str) -> bool:
    """Write the report as JSON to ``filename``; return whether it succeeded."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        return True
    except Exception as e:
        print("Failed to save JSON:", e, file=sys.stderr)
        return False


def save_yaml_file(data: dict[str, Any], filename: str) -> bool:
    """Write the report as YAML to ``filename``; return whether it succeeded."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            compatible = json.loads(json.dumps(data, default=str))
            yaml.safe_dump(compatible, f, sort_keys=False, allow_unicode=True)
        return True
    except Exception as e:
        print("Failed to save YAML:", e, file=sys.stderr)
        return False


def _sanitize_xml_name(name: str) -> str:
    sanitized = _INVALID_XML_NAME.sub("_", str(name))
    if not sanitized or sanitized[0].isdigit() or sanitized[0] in ".-":
        sanitized = f"_{sanitized}"
    return sanitized


def _scalar_xml_text(value: object) -> str:
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return _sanitize_xml_text(str(value))


def _append_xml_value(parent: ET.Element, value: object) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            child = ET.SubElement(parent, _sanitize_xml_name(key))
            _append_xml_value(child, child_value)
    elif isinstance(value, list):
        for item in value:
            child = ET.SubElement(parent, "item")
            _append_xml_value(child, item)
    else:
        parent.text = _scalar_xml_text(value)


def dumps_xml(data: dict[str, Any]) -> str:
    """Serialise the report as an indented XML document."""
    root = ET.Element("sysinfo")
    _append_xml_value(root, data)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def save_xml_file(data: dict[str, Any], filename: str) -> bool:
    """Write the report as XML to ``filename``; return whether it succeeded."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(dumps_xml(data))
            f.write("\n")
        return True
    except Exception as e:
        print("Failed to save XML:", e, file=sys.stderr)
        return False
