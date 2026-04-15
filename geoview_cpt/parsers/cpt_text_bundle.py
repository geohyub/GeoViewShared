"""
geoview_cpt.parsers.cpt_text_bundle
======================================
Vendor-agnostic ``.cdf + .CLog`` bundle reader (Phase A-2 A2.2d).

Gouda WISON exports every sounding as a folder with:

    CPT010001.rdf    raw binary (not consumed here)
    CPT010001.cdf    computed CSV data  (rows = per-sample readings)
    CPT010001.CLog   acquisition log    (rows = timestamped events)
    CPT010001.RD2D   2-D viewer cache   (ignored)
    CPT010001.bmp    operator screenshot (ignored)

This module owns the text sub-bundle (``.cdf`` + ``.CLog``):

    parse_clog_events    text log → list[AcquisitionEvent]
    parse_cdf_bundle     ``.cdf`` + optional ``.CLog`` → :class:`CPTSounding`
                         with populated ``header.events``

The ``.cdf`` file is a CSV variant of the vendor's XLS export —
identical metadata block, identical data header, identical units —
so this reader produces a :class:`CPTSounding` that matches
:func:`geoview_cpt.parsers.excel_jako.parse_jako_xls` on the same
borehole. A future :mod:`cpt_text_bundle.smoke_test` pytest asserts
byte-for-byte agreement on JAKO CPT01.

This closes the **A2.6 drift check stub** dependency: with
``sounding.header.events`` populated, the drift checks in
:mod:`geoview_cpt.qc_rules.checks` switch from "info gap" placeholders
to real first-vs-last baseline comparisons.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from geoview_cpt.model import (
    AcquisitionEvent,
    CPTChannel,
    CPTHeader,
    CPTSounding,
    EventType,
)

__all__ = [
    "CptBundleParseError",
    "parse_clog_events",
    "parse_cdf_bundle",
    "CLOG_EVENT_TYPE_MAP",
]


class CptBundleParseError(Exception):
    """Raised when a ``.cdf`` / ``.CLog`` bundle cannot be read."""


# ---------------------------------------------------------------------------
# CLog event vocabulary
# ---------------------------------------------------------------------------


CLOG_EVENT_TYPE_MAP: dict[str, EventType] = {
    # Canonical vocabulary from AcquisitionEvent.EventType Literal
    "Thrust":                        "Thrust",
    "Stop Thrust":                   "Thrust",
    "Retract":                       "Retract",
    "Deck Baseline":                 "Deck Baseline",
    "Seabed Baseline":               "Seabed Baseline",
    "Post Baseline":                 "Post Baseline",
    "Cone Up":                       "Cone Up",
    "Maximum Push Distance Reached": "Max Push Distance Reached",
    "Max Push Distance Reached":     "Max Push Distance Reached",
    "CHANGE CONE":                   "CHANGE CONE",
    "Operator Note":                 "Operator Note",
}


_TIMESTAMP_RE = re.compile(
    r"^(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2}):(\d{2})$"
)
_DATA_TIMESTAMP_RE = re.compile(
    r"^#(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2}):(\d{2})#$"
)


# ---------------------------------------------------------------------------
# CLog
# ---------------------------------------------------------------------------


def parse_clog_events(path: Path | str) -> list[AcquisitionEvent]:
    """
    Parse a Gouda WISON ``.CLog`` file into :class:`AcquisitionEvent`.

    The CLog format is a two-column CSV with a ``Date/Time,Details``
    header. Details are either a short label (``Deck Baseline``,
    ``Thrust``) or a multi-line block delimited by ``<`` / ``>`` — the
    first entry is typically a Telemetry Auto-Tuning Report.

    Multi-line blocks are collapsed to the first meaningful line +
    preserved verbatim on :attr:`AcquisitionEvent.message`. Unknown
    event labels map to ``"Other"`` so the reader never rejects a
    vendor sounding.
    """
    p = Path(path)
    if not p.exists():
        raise CptBundleParseError(f"file not found: {p}")

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise CptBundleParseError(f"cannot read {p}: {exc}") from exc

    events: list[AcquisitionEvent] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("Date/Time"):
            i += 1
            continue
        # Tokenize on the first comma only
        if "," not in line:
            i += 1
            continue
        ts_token, details = line.split(",", 1)
        ts_token = ts_token.strip()
        details = details.strip()

        ts = _parse_clog_timestamp(ts_token)
        if ts is None:
            i += 1
            continue

        if details.startswith("<") and not details.endswith(">"):
            # Multi-line block — collect until a ">" end-delimiter
            body_lines: list[str] = [details.lstrip("<").rstrip()]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].rstrip()
                if nxt.startswith(">"):
                    break
                body_lines.append(nxt)
                j += 1
            i = j + 1   # consume the trailing `>` line
            message = "\n".join(body_lines).strip()
            event_type: EventType = "Other"
            # Look for a "COMPLETION CODE" or similar marker to tag it
            if "TELEMETRY" in message.upper():
                event_type = "Other"
            events.append(
                AcquisitionEvent(
                    timestamp=ts,
                    event_type=event_type,
                    message=message,
                )
            )
            continue

        # Single-line event
        i += 1
        clean = details.strip("<>").strip()
        event_type = CLOG_EVENT_TYPE_MAP.get(clean, "Other")
        events.append(
            AcquisitionEvent(
                timestamp=ts,
                event_type=event_type,
                message=clean if event_type == "Other" else "",
            )
        )

    return events


def _parse_clog_timestamp(token: str) -> datetime | None:
    m = _TIMESTAMP_RE.match(token)
    if not m:
        return None
    dd, mm, yyyy, hh, mi, ss = (int(g) for g in m.groups())
    try:
        return datetime(yyyy, mm, dd, hh, mi, ss)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# .cdf  (CSV variant of the vendor XLS)
# ---------------------------------------------------------------------------


@dataclass
class _MetaBlock:
    project_name: str = ""
    client_name: str = ""
    location: str = ""
    vessel: str = ""
    client: str = ""
    operator: str = ""
    cone: str = ""
    notes: str = ""
    water_depth: float | None = None
    push_name: str = ""
    max_tip_mpa: str = ""
    tip_area_mm2: float = 200.0
    tip_area_factor: float = 0.7032
    hydrostatic_mpa: float = 0.0
    software_version: str = ""


def parse_cdf_bundle(
    cdf_path: Path | str,
    *,
    clog_path: Path | str | None = None,
    partner_name: str = "Geoview",
    equipment_vendor: str = "Gouda Geo-Equipment",
    equipment_model: str = "WISON-APB",
) -> CPTSounding:
    """
    Read a Gouda WISON ``.cdf`` CSV file into a :class:`CPTSounding`.

    Args:
        cdf_path:          filesystem path to the ``.cdf`` file.
        clog_path:         optional ``.CLog`` sibling. When provided,
                           :func:`parse_clog_events` is run and the
                           events are attached to ``sounding.header.events``.
                           If omitted, the reader auto-discovers the
                           sibling by replacing the suffix.
        partner_name:      stamped onto :class:`CPTHeader`; default
                           ``"Geoview"`` matches JAKO Korea projects.
        equipment_vendor:  default ``"Gouda Geo-Equipment"``.
        equipment_model:   default ``"WISON-APB"``.

    Returns:
        :class:`CPTSounding` with depth/qc/fs/u2/incl channels in the
        canonical parser units (qc MPa, fs kPa, u2 kPa) and events
        attached when the ``.CLog`` sibling was present.
    """
    p = Path(cdf_path)
    if not p.exists():
        raise CptBundleParseError(f"file not found: {p}")

    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise CptBundleParseError(f"cannot read {p}: {exc}") from exc

    lines = text.splitlines()
    meta, data_header_idx = _parse_cdf_meta(lines, p)
    depth, qc, fs, u2, incl, first_ts, last_ts = _parse_cdf_data(
        lines, data_header_idx
    )

    if depth.size == 0:
        raise CptBundleParseError(f"{p}: no data rows")

    sounding_id = meta.push_name or meta.project_name or p.stem
    header = CPTHeader(
        sounding_id=sounding_id,
        project_name=meta.project_name,
        client=meta.client_name or meta.client,
        partner_name=partner_name,
        operator=meta.operator,
        vessel=meta.vessel,
        water_depth_m=meta.water_depth,
        sounding_type="PCPT",
        equipment_vendor=equipment_vendor,
        equipment_model=equipment_model,
        cone_base_area_mm2=meta.tip_area_mm2,
        cone_area_ratio_a=meta.tip_area_factor,
        started_at=first_ts,
        completed_at=last_ts,
        max_push_depth_m=float(depth.max()),
    )

    sounding = CPTSounding(
        handle=0,
        element_tag="",
        name=sounding_id,
        file_name=p.name,
        input_count=int(depth.size),
        output_count=int(depth.size),
        max_depth_m=float(depth.max()),
        unit_system=0,
    )
    sounding.header = header
    sounding.channels = {
        "depth": CPTChannel(name="depth", unit="m",   values=depth),
        "qc":    CPTChannel(name="qc",    unit="MPa", values=qc),
        "fs":    CPTChannel(name="fs",    unit="kPa", values=fs * 1000.0),
        "u2":    CPTChannel(name="u2",    unit="kPa", values=u2 * 1000.0),
        "incl":  CPTChannel(name="incl",  unit="deg", values=incl),
    }
    sounding.metadata.update(
        {
            "source_format": "cdf_bundle",
            "source_path": str(p),
            "software_version": meta.software_version,
            "raw_meta": meta.__dict__,
        }
    )

    # Attach CLog events if present
    resolved_clog = _resolve_clog_path(p, clog_path)
    if resolved_clog is not None and resolved_clog.exists():
        header.events.extend(parse_clog_events(resolved_clog))
        sounding.metadata["clog_path"] = str(resolved_clog)

    return sounding


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------


def _resolve_clog_path(
    cdf_path: Path, clog_override: Path | str | None
) -> Path | None:
    if clog_override is not None:
        return Path(clog_override)
    sibling = cdf_path.with_suffix(".CLog")
    if sibling.exists():
        return sibling
    lowered = cdf_path.with_suffix(".clog")
    if lowered.exists():
        return lowered
    return None


def _parse_cdf_meta(lines: list[str], path: Path) -> tuple[_MetaBlock, int]:
    meta = _MetaBlock()
    data_header_idx = -1
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        cells = _parse_csv_line(line)
        if not cells:
            i += 1
            continue
        first = cells[0].strip()

        if first == "Software Version":
            if i + 1 < len(lines):
                meta.software_version = _parse_csv_line(lines[i + 1])[0].strip()
            i += 2
            continue

        if first == "Project Name" and len(cells) >= 4:
            # Next line holds the values
            if i + 1 < len(lines):
                vals = _parse_csv_line(lines[i + 1])
                vals = _pad(vals, len(cells))
                meta.project_name = _strip(vals[0])
                meta.client_name = _strip(vals[1]) if len(cells) > 1 else ""
                meta.location = _strip(vals[2]) if len(cells) > 2 else ""
                meta.vessel = _strip(vals[3]) if len(cells) > 3 else ""
                meta.client = _strip(vals[4]) if len(cells) > 4 else ""
                meta.operator = _strip(vals[5]) if len(cells) > 5 else ""
                meta.cone = _strip(vals[6]) if len(cells) > 6 else ""
                meta.notes = _strip(vals[7]) if len(cells) > 7 else ""
            i += 2
            continue

        if first == "Fix Number":
            if i + 1 < len(lines):
                vals = _parse_csv_line(lines[i + 1])
                vals = _pad(vals, 9)
                meta.water_depth = _float_or_none(vals[1])
                meta.push_name = _strip(vals[2])
                meta.max_tip_mpa = _strip(vals[6])
            i += 2
            continue

        if first == "Tip Area (mm)":
            if i + 1 < len(lines):
                vals = _parse_csv_line(lines[i + 1])
                meta.tip_area_mm2 = _float_or_default(vals[0] if vals else "", 200.0)
            i += 2
            continue

        if first == "Tip Area Factor":
            if len(cells) > 1:
                meta.tip_area_factor = _float_or_default(cells[1].strip(), 0.7032)
            i += 1
            continue

        if first == "Hydrostatic Pressure (MPa)":
            if len(cells) > 1:
                meta.hydrostatic_mpa = _float_or_default(cells[1].strip(), 0.0)
            i += 1
            continue

        if first == "Date&Time":
            data_header_idx = i
            break

        i += 1

    if data_header_idx < 0:
        raise CptBundleParseError(
            f"{path}: 'Date&Time' data header not found"
        )
    return meta, data_header_idx


def _parse_cdf_data(
    lines: list[str], data_header_idx: int
) -> tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray,
    datetime | None, datetime | None,
]:
    header_cells = _parse_csv_line(lines[data_header_idx])
    col_of = {}
    for idx, cell in enumerate(header_cells):
        low = cell.strip().lower()
        if "date" in low and "time" in low:
            col_of["time"] = idx
        elif low.startswith("pen"):
            col_of["depth"] = idx
        elif "tip" in low and "qc" in low:
            col_of["qc"] = idx
        elif "sleeve" in low:
            col_of["fs"] = idx
        elif "pore" in low:
            col_of["u2"] = idx
        elif "combined" in low and "tilt" in low:
            col_of["incl"] = idx

    required = {"depth", "qc", "fs", "u2"}
    missing = required - set(col_of)
    if missing:
        raise CptBundleParseError(
            f"data header missing required columns: {missing}"
        )

    depths: list[float] = []
    qcs: list[float] = []
    fss: list[float] = []
    u2s: list[float] = []
    incls: list[float] = []
    first_ts: datetime | None = None
    last_ts: datetime | None = None

    for line in lines[data_header_idx + 1:]:
        if not line.strip():
            continue
        cells = _parse_csv_line(line)
        if len(cells) <= col_of["depth"]:
            continue
        d_val = _float_or_none(cells[col_of["depth"]])
        if d_val is None:
            continue
        depths.append(d_val)
        qcs.append(_float_or_default(cells[col_of["qc"]], 0.0))
        fss.append(_float_or_default(cells[col_of["fs"]], 0.0))
        u2s.append(_float_or_default(cells[col_of["u2"]], 0.0))
        incls.append(
            _float_or_default(cells[col_of["incl"]], 0.0)
            if "incl" in col_of and len(cells) > col_of["incl"]
            else 0.0
        )
        if "time" in col_of and len(cells) > col_of["time"]:
            ts = _parse_cdf_timestamp(cells[col_of["time"]])
            if ts is not None:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

    return (
        np.asarray(depths, dtype=np.float64),
        np.asarray(qcs, dtype=np.float64),
        np.asarray(fss, dtype=np.float64),
        np.asarray(u2s, dtype=np.float64),
        np.asarray(incls, dtype=np.float64),
        first_ts,
        last_ts,
    )


def _parse_csv_line(line: str) -> list[str]:
    reader = csv.reader([line])
    try:
        return next(reader)
    except StopIteration:
        return []


def _strip(value: Any) -> str:
    return str(value).strip().strip('"') if value is not None else ""


def _pad(cells: list[str], n: int) -> list[str]:
    return cells + [""] * max(0, n - len(cells))


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip().strip('"')
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _float_or_default(value: Any, default: float) -> float:
    result = _float_or_none(value)
    return result if result is not None else default


def _parse_cdf_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    s = str(value).strip().strip('"')
    m = _DATA_TIMESTAMP_RE.match(s)
    if not m:
        return None
    dd, mm, yyyy, hh, mi, ss = (int(g) for g in m.groups())
    try:
        return datetime(yyyy, mm, dd, hh, mi, ss)
    except ValueError:
        return None
