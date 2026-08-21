"""Tests for JSON/YAML export helpers."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from enum import IntEnum
from pathlib import Path

import yaml

from lupaxa.sysinfo.export import (
    dumps_json,
    dumps_xml,
    dumps_yaml,
    export_html,
    save_json_file,
    save_xml_file,
    save_yaml_file,
)


class AddressFamily(IntEnum):
    """Stand-in for ``socket.AddressFamily`` values found in collector output."""

    AF_INET = 2


def _parse(xml: str) -> ET.Element:
    """Parse XML that this test module produced via ``dumps_xml``."""
    return ET.fromstring(xml)  # noqa: S314 - input comes from our own exporter


def test_dumps_json_round_trip() -> None:
    """JSON export round-trips through ``json.loads``."""
    data = {"schema_version": 1, "basic": {"hostname": "host"}}
    loaded = json.loads(dumps_json(data))
    assert loaded == data


def test_dumps_yaml_round_trip() -> None:
    """YAML export round-trips through ``yaml.safe_load``."""
    data = {"schema_version": 1, "basic": {"hostname": "host"}}
    loaded = yaml.safe_load(dumps_yaml(data))
    assert loaded == data


def test_save_json_and_yaml_files(tmp_path: Path) -> None:
    """The JSON and YAML file writers persist the report verbatim."""
    data = {"ok": True, "n": 1}
    j = tmp_path / "out.json"
    y = tmp_path / "out.yaml"
    assert save_json_file(data, str(j)) is True
    assert save_yaml_file(data, str(y)) is True
    assert json.loads(j.read_text(encoding="utf-8")) == data
    assert yaml.safe_load(y.read_text(encoding="utf-8")) == data


def test_yaml_export_converts_nested_int_enums(tmp_path: Path) -> None:
    """Nested ``IntEnum`` values are emitted as plain integers."""
    data = {"network": {"interfaces": [{"family": AddressFamily.AF_INET}]}}
    output = tmp_path / "enum.yaml"

    assert yaml.safe_load(dumps_yaml(data)) == {"network": {"interfaces": [{"family": 2}]}}
    assert save_yaml_file(data, str(output)) is True
    assert yaml.safe_load(output.read_text(encoding="utf-8")) == {
        "network": {"interfaces": [{"family": 2}]}
    }


def test_dumps_xml_basic_structure() -> None:
    """XML export nests scalar values under a ``sysinfo`` root."""
    xml = dumps_xml({"schema_version": 1, "basic": {"hostname": "h"}})
    assert "<sysinfo>" in xml
    assert "<schema_version>1</schema_version>" in xml
    assert "<hostname>h</hostname>" in xml


def test_dumps_xml_lists_as_items() -> None:
    """List entries are emitted as repeated ``item`` elements."""
    xml = dumps_xml({"values": [1, 2]})
    assert xml.count("<item>") == 2


def test_dumps_xml_strips_illegal_control_characters() -> None:
    """Characters outside the XML 1.0 Char production are dropped."""
    xml = dumps_xml({"cmd": "boot\x00strap\x1b[0m done\x08"})
    root = _parse(xml)
    assert root.findtext("cmd") == "bootstrap[0m done"


def test_dumps_xml_keeps_legal_whitespace() -> None:
    """Tabs and newlines survive the control-character filter."""
    xml = dumps_xml({"blob": "a\tb\nc\rd"})
    root = _parse(xml)
    text = root.findtext("blob")
    assert text is not None
    assert "\t" in text
    assert "\n" in text


def test_dumps_xml_sanitizes_leading_hyphen_key() -> None:
    """Keys starting with a hyphen gain an underscore prefix."""
    xml = dumps_xml({"-o": "value"})
    root = _parse(xml)
    assert [child.tag for child in root] == ["_-o"]


def test_dumps_xml_sanitizes_leading_digit_and_dot_keys() -> None:
    """Keys starting with a digit or dot gain an underscore prefix."""
    xml = dumps_xml({"3rd": 1, ".hidden": 2})
    root = _parse(xml)
    assert [child.tag for child in root] == ["_3rd", "_.hidden"]


def test_dumps_xml_escapes_markup_in_text() -> None:
    """Markup inside text values is escaped rather than emitted raw."""
    xml = dumps_xml({"note": "<b>a & b</b>"})
    root = _parse(xml)
    assert root.findtext("note") == "<b>a & b</b>"


def test_save_xml_file(tmp_path: Path) -> None:
    """The XML file writer persists a well-formed document."""
    data = {"ok": True, "n": 1}
    output = tmp_path / "out.xml"
    assert save_xml_file(data, str(output)) is True
    text = output.read_text(encoding="utf-8")
    assert "<sysinfo>" in text
    assert "<ok>true</ok>" in text


def test_export_html_includes_services_section(tmp_path: Path) -> None:
    """The HTML report renders a section for each populated key."""
    output = tmp_path / "report.html"

    assert export_html({"services": {"running": ["sshd"]}}, str(output)) is True
    assert ">Services</h2>" in output.read_text(encoding="utf-8")
