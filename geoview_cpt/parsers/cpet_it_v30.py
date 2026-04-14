"""
geoview_cpt.parsers.cpet_it_v30
===================================
Reader for CPeT-IT v.3.9.1.3 ``.cpt`` files (Phase A-2 A2.0).

Pipeline:

    zlib deflate  ──► UTF-8 XML (invalid per W3C — numeric tags)
                ──► _xml_sanitize.mangle  (``<87616>`` → ``<n_87616>``)
                ──► lxml.etree
                ──► CPTProject / CPTSounding

What we extract:

 - ``<Various>`` metadata → :class:`CPTProject` fields
   (handle, project name, branding 4 fields, unit system, fonts,
   custom SBTn descriptor slots, …).
 - ``<Various>`` element serialized bytes → ``CPTProject.various_raw``
   for byte-exact round-trip of the global section.
 - Every ``<CPTFiles>/<NNNNN>`` child → one :class:`CPTSounding`.
   For each sounding we capture:
     * ``handle`` and the original element tag (``"87616"``) so writers
       can reproduce the XML structure.
     * the well-known header fields (``CPTName``, ``CPTFileName``,
       ``InputCount``, ``OutputCount``, ``MaxDepth``, ``UnitSystem``,
       ``ConeCorrected``).
     * every ``<CPTProperties>`` child flattened to a ``{tag: text}`` dict
       — this is the Nkt/Alpha/Elevation/GWT/Kocr bundle.
     * ``<ChartPropertiesLeft>`` and ``<ChartPropertiesBottom>`` as raw
       bytes for chart-metadata preservation.
     * the ``.text`` of the ``<NNNNN>`` element (stored as
       ``blob_b64``) — this is the base64 payload whose binary
       structure is reverse-engineered in A2.0b.
     * every *other* immediate child of ``<NNNNN>`` serialized to
       ``extras[tag]`` so future parsers can interpret them in isolation.
 - Other top-level ``<CPT>`` children (``WebGMap``, ``OverlayProps``,
   ``CustomData1``, …) stored as ``extra_sections[tag]`` raw bytes.

What we **don't** do yet:

 - Decode the per-sample binary blob → numeric arrays. That's A2.0b.
 - Write a ``.cpt`` file. That's A2.0c.
 - Build :class:`geoview_cpt.model.CPTChannel` / ``CPTHeader`` (A2.1).

Known CPeT-IT quirks handled here:

 - XML is *not* valid per W3C (numeric tags). See :mod:`_xml_sanitize`.
 - ``<Path>`` branding field is an absolute path on the *author's*
   machine and should not be trusted as a filesystem reference.
 - Mixed content on ``<NNNNN>``: CPeT-IT emits the base64 blob as
   element text *before* the first structural child. lxml exposes that
   as ``element.text``; we preserve it verbatim.
"""
from __future__ import annotations

import base64
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree as ET

from geoview_cpt.model.project import CPTProject, CPTSounding
from geoview_cpt.parsers._xml_sanitize import mangle, original_tag

__all__ = [
    "CPetItReadError",
    "read_cpt_v30",
    "read_cpt_v30_bytes",
]


# Sounding-block header fields we lift to named CPTSounding attributes.
_HEADER_FIELDS = {
    "Handle",
    "CPTName",
    "CPTFileName",
    "InputCount",
    "OutputCount",
    "MaxDepth",
    "UnitSystem",
    "ConeCorrected",
    "CPTProperties",
    "ChartPropertiesLeft",
    "ChartPropertiesBottom",
}


class CPetItReadError(Exception):
    """Raised when a ``.cpt`` file cannot be read or parsed."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_cpt_v30(path: Path | str) -> CPTProject:
    """
    Read a CPeT-IT v30 ``.cpt`` file into a :class:`CPTProject`.

    Raises:
        CPetItReadError: on missing/unreadable files, zlib failures, or
                         malformed XML that mangling cannot rescue.
    """
    p = Path(path)
    if not p.exists():
        raise CPetItReadError(f"file not found: {p}")
    try:
        raw = p.read_bytes()
    except OSError as exc:
        raise CPetItReadError(f"cannot read {p}: {exc}") from exc
    project = read_cpt_v30_bytes(raw)
    project.source_path = p
    return project


def read_cpt_v30_bytes(raw: bytes) -> CPTProject:
    """Read a ``.cpt`` payload already in memory."""
    if not raw:
        raise CPetItReadError("empty input")

    plain = _inflate(raw)
    try:
        mangled = mangle(plain.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise CPetItReadError(f"inflated payload is not UTF-8: {exc}") from exc

    try:
        root = ET.fromstring(mangled.encode("utf-8"))
    except ET.XMLSyntaxError as exc:
        raise CPetItReadError(f"XML parse failure: {exc}") from exc

    if root.tag != "CPT":
        raise CPetItReadError(
            f"root element is {root.tag!r}, expected 'CPT'"
        )
    version = root.attrib.get("Version", "")
    if version != "30":
        raise CPetItReadError(
            f"unsupported CPT Version {version!r}; this reader handles '30'"
        )

    project = CPTProject(
        xml_plain=plain,
        raw_compressed=raw,
    )
    _fill_various(project, root)
    _fill_soundings(project, root)
    _fill_extras(project, root)
    return project


# ---------------------------------------------------------------------------
# zlib layer
# ---------------------------------------------------------------------------


def _inflate(raw: bytes) -> bytes:
    try:
        return zlib.decompress(raw)
    except zlib.error as exc:
        raise CPetItReadError(f"zlib inflate failed: {exc}") from exc


# ---------------------------------------------------------------------------
# <Various>
# ---------------------------------------------------------------------------


def _fill_various(project: CPTProject, root: ET._Element) -> None:
    various = root.find("Various")
    if various is None:
        raise CPetItReadError("missing <Various> block")

    project.various_raw = ET.tostring(various)

    project.handle = _int(various.findtext("Handle"))
    project.name = _text(various.findtext("Project"))
    project.project_id = _text(various.findtext("ProjectID"))
    project.location = _text(various.findtext("Location"))
    project.comments = _text(various.findtext("Comments"))
    project.partner_brand = _text(various.findtext("First"))
    project.partner_description = _text(various.findtext("Second"))
    project.partner_address = _text(various.findtext("Third"))
    project.partner_url = _text(various.findtext("Forth"))
    project.partner_logo_path = _text(various.findtext("Path"))
    project.unit_system = _int(various.findtext("Unit_System"))
    project.vertical_plot = _bool_flag(various.findtext("Vertical_Plot"))
    project.display_image = _bool_flag(various.findtext("DisplayImage"))
    project.font_name = _text(various.findtext("FontName"))
    project.font_size = _int(various.findtext("FontSize"))
    custom = _text(various.findtext("CustomSBTnDesc"))
    project.custom_sbtn_desc = custom.split(";") if custom else []


# ---------------------------------------------------------------------------
# <CPTFiles>
# ---------------------------------------------------------------------------


def _fill_soundings(project: CPTProject, root: ET._Element) -> None:
    container = root.find("CPTFiles")
    if container is None:
        return

    for node in container:
        sounding = _build_sounding(node)
        project.soundings.append(sounding)
        try:
            project.cptfiles_raw[sounding.element_tag] = base64.b64decode(
                sounding.blob_b64, validate=False
            )
        except (base64.binascii.Error, ValueError):
            # Keep going: A2.0b will revisit blob decoding.
            project.cptfiles_raw[sounding.element_tag] = b""


def _build_sounding(node: ET._Element) -> CPTSounding:
    element_tag = original_tag(node.tag)
    try:
        handle = int(element_tag)
    except ValueError:
        handle = 0

    sounding = CPTSounding(
        handle=handle,
        element_tag=element_tag,
        blob_b64=(node.text or "").strip(),
    )

    for child in node:
        tag = child.tag
        if tag == "CPTName":
            sounding.name = _text(child.text)
        elif tag == "CPTFileName":
            sounding.file_name = _text(child.text)
        elif tag == "InputCount":
            sounding.input_count = _int(child.text)
        elif tag == "OutputCount":
            sounding.output_count = _int(child.text)
        elif tag == "MaxDepth":
            sounding.max_depth_m = _float(child.text)
        elif tag == "UnitSystem":
            sounding.unit_system = _int(child.text)
        elif tag == "Handle":
            # Redundant with element_tag but CPeT-IT emits both.
            try:
                sounding.handle = int(_text(child.text) or 0)
            except ValueError:
                pass
        elif tag == "ConeCorrected":
            sounding.cone_corrected = _bool_flag(child.text)
        elif tag == "CPTProperties":
            for prop in child:
                sounding.properties[prop.tag] = _text(prop.text)
        elif tag == "ChartPropertiesLeft":
            sounding.chart_config_raw["left"] = ET.tostring(child)
        elif tag == "ChartPropertiesBottom":
            sounding.chart_config_raw["bottom"] = ET.tostring(child)
        else:
            sounding.extras[tag] = ET.tostring(child)

    return sounding


# ---------------------------------------------------------------------------
# extra top-level sections
# ---------------------------------------------------------------------------


def _fill_extras(project: CPTProject, root: ET._Element) -> None:
    for child in root:
        if child.tag in ("Various", "CPTFiles"):
            continue
        project.extra_sections[child.tag] = ET.tostring(child)


# ---------------------------------------------------------------------------
# primitive coercion helpers
# ---------------------------------------------------------------------------


def _text(value: str | None) -> str:
    return "" if value is None else str(value)


def _int(value: str | None) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value))
        except ValueError:
            return 0


def _float(value: str | None) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _bool_flag(value: str | None) -> bool:
    if value is None:
        return False
    v = value.strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no", ""):
        return False
    return False
