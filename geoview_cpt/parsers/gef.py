"""
geoview_cpt.parsers.gef
================================
Dutch Geotechnical Exchange Format (GEF) reader — Phase A-2 A2.3.

Reference: SBRCURnet CUR 2001-R23 + NEN 3650. GEF is a 1994 text
format that is still the de-facto exchange standard between Dutch
geotechnical vendors and clients.

Structure:

    # header_keyword                                 ← '#'-prefixed header
    # COLUMNINFO=1, m, depth, 1                       ← column spec lines
    # COLUMNVOID= 1, -9999
    # EOH= ← end-of-header marker
    data_row_1                                        ← space/tab separated numeric
    data_row_2
    ...

Key headers we extract:

    FILEDATE    ISO-like date string
    PROCEDURECODE / REPORTCODE   e.g. "GEF-CPT-Report"
    MEASUREMENTTEXT             project name / borehole id
    XYID / COMPANYID / LOCATION
    COLUMNINFO                   (column index, unit, quantity, class)
    COLUMNVOID                   missing-data sentinel
    LASTSCAN                     row count (optional)
    EOH                          end-of-header — data begins next line

Column layout varies per vendor; the reader maps whatever combination
of ``depth / qc / fs / u2`` the file declares by matching the third
``COLUMNINFO`` field (the quantity string) against a small dictionary.
Missing channels are silently dropped.

Scope (v1): tip-only soundings are supported (``depth`` + ``qc``).
Soundings missing fs or u2 still produce a valid :class:`CPTSounding`
with the available channels. Full 15-column PDA-GEF profiles flow
through unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np

from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding

__all__ = [
    "GefParseError",
    "parse_gef",
]


class GefParseError(Exception):
    """Raised when a ``.gef`` file cannot be parsed."""


_COLUMN_INFO_RE = re.compile(
    r"^\s*(?P<index>\d+)\s*,\s*(?P<unit>[^,]+)\s*,\s*(?P<quantity>[^,]+)\s*,\s*(?P<class_>[^,]+)\s*$"
)


_QUANTITY_MAP: dict[str, str] = {
    # GEF-CPT-Report ``COLUMNINFO`` quantity strings
    "gecorrigeerde sondeerlengte": "depth",
    "penetration length":           "depth",
    "length":                       "depth",
    "depth":                        "depth",
    "conusweerstand":               "qc",
    "cone resistance":              "qc",
    "measured cone resistance":     "qc",
    "cone pressure":                "qc",
    "qc":                           "qc",
    "wrijvingsweerstand":           "fs",
    "local friction":               "fs",
    "sleeve friction":              "fs",
    "fs":                           "fs",
    "waterspanning u2":             "u2",
    "pore pressure u2":             "u2",
    "measured pore pressure":       "u2",
    "u2":                           "u2",
    "helling":                      "incl",
    "inclination":                  "incl",
    "tilt":                         "incl",
}


@dataclass
class _ColumnSpec:
    index: int
    unit: str
    quantity: str
    canonical: str | None = None   # "depth" / "qc" / "fs" / "u2" / "incl"


@dataclass
class _Header:
    project_name: str = ""
    company: str = ""
    location: str = ""
    operator: str = ""
    measurement_id: str = ""
    void_values: dict[int, float] = field(default_factory=dict)
    columns: list[_ColumnSpec] = field(default_factory=list)


def parse_gef(path: Path | str) -> CPTSounding:
    """
    Read a ``.gef`` CPT file into a :class:`CPTSounding`.

    Args:
        path: filesystem path to a ``.gef`` file.

    Returns:
        :class:`CPTSounding` with whatever canonical channels the file
        declares (always ``depth``, plus any of ``qc`` / ``fs`` / ``u2``
        / ``incl``).

    Raises:
        GefParseError: missing / unreadable file, no ``#EOH``,
                       no ``COLUMNINFO`` lines, or empty data block.
    """
    p = Path(path)
    if not p.exists():
        raise GefParseError(f"file not found: {p}")
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise GefParseError(f"cannot read {p}: {exc}") from exc

    header, data_lines = _split_header_data(text, p)
    if not header.columns:
        raise GefParseError(f"{p}: no COLUMNINFO headers found")
    _assign_canonical_columns(header.columns)

    arrays = _read_data_rows(header, data_lines, p)
    if "depth" not in arrays or arrays["depth"].size == 0:
        raise GefParseError(f"{p}: no depth column or empty data block")

    depth = arrays["depth"]
    cpth_header = CPTHeader(
        sounding_id=header.measurement_id or p.stem,
        project_name=header.project_name,
        client="",
        operator=header.operator,
        sounding_type="PCPT",
        max_push_depth_m=float(depth.max()),
    )

    sounding = CPTSounding(
        handle=0,
        element_tag="",
        name=header.measurement_id or p.stem,
        file_name=p.name,
        input_count=int(depth.size),
        output_count=int(depth.size),
        max_depth_m=float(depth.max()),
        unit_system=0,
    )
    sounding.header = cpth_header

    channels: dict[str, CPTChannel] = {
        "depth": CPTChannel(name="depth", unit="m", values=depth),
    }
    if "qc" in arrays:
        channels["qc"] = CPTChannel(name="qc", unit="MPa", values=arrays["qc"])
    if "fs" in arrays:
        # GEF stores fs in MPa — convert to kPa (canonical)
        channels["fs"] = CPTChannel(name="fs", unit="kPa", values=arrays["fs"] * 1000.0)
    if "u2" in arrays:
        channels["u2"] = CPTChannel(name="u2", unit="kPa", values=arrays["u2"] * 1000.0)
    if "incl" in arrays:
        channels["incl"] = CPTChannel(name="incl", unit="deg", values=arrays["incl"])

    sounding.channels = channels
    sounding.metadata.update(
        {
            "source_format": "gef",
            "source_path": str(p),
            "company": header.company,
            "location": header.location,
        }
    )
    return sounding


# ---------------------------------------------------------------------------
# header / body split
# ---------------------------------------------------------------------------


def _split_header_data(text: str, path: Path) -> tuple[_Header, list[str]]:
    header = _Header()
    data_lines: list[str] = []
    in_data = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if in_data:
            data_lines.append(line)
            continue
        if line.startswith("#"):
            # Strip leading '#' + optional space
            body = line.lstrip("#").strip()
            if not body:
                continue
            key, _, val = body.partition("=")
            key = key.strip().upper()
            val = val.strip()
            if key == "EOH":
                in_data = True
            elif key == "MEASUREMENTTEXT":
                header.measurement_id = _strip_leading_index(val) or header.measurement_id
            elif key == "PROJECTNAME":
                header.project_name = val
            elif key == "PROJECTID":
                header.project_name = header.project_name or val
            elif key == "COMPANYID":
                header.company = val
            elif key == "LOCATION":
                header.location = val
            elif key == "OPERATOR":
                header.operator = val
            elif key == "COLUMNINFO":
                m = _COLUMN_INFO_RE.match(val)
                if m:
                    header.columns.append(
                        _ColumnSpec(
                            index=int(m.group("index")),
                            unit=m.group("unit").strip(),
                            quantity=m.group("quantity").strip(),
                        )
                    )
            elif key == "COLUMNVOID":
                parts = [s.strip() for s in val.split(",")]
                if len(parts) == 2:
                    try:
                        header.void_values[int(parts[0])] = float(parts[1])
                    except ValueError:
                        pass
            # Other keys ignored for v1
        else:
            # Some GEF files have stray lines before the first '#' —
            # be tolerant
            continue
    if not in_data:
        raise GefParseError(f"{path}: EOH marker missing")
    return header, data_lines


def _strip_leading_index(value: str) -> str:
    """``MEASUREMENTTEXT=1, BH-01`` → ``BH-01``."""
    parts = [s.strip() for s in value.split(",", 1)]
    if len(parts) == 2:
        return parts[1]
    return parts[0]


# ---------------------------------------------------------------------------
# Column assignment
# ---------------------------------------------------------------------------


def _assign_canonical_columns(columns: Iterable[_ColumnSpec]) -> None:
    for col in columns:
        key = col.quantity.strip().lower()
        # Try exact match first
        if key in _QUANTITY_MAP:
            col.canonical = _QUANTITY_MAP[key]
            continue
        # Substring fallback for vendors that embed units in the name
        for token, canonical in _QUANTITY_MAP.items():
            if token in key and col.canonical is None:
                col.canonical = canonical
                break


# ---------------------------------------------------------------------------
# Data rows
# ---------------------------------------------------------------------------


def _read_data_rows(
    header: _Header, data_lines: list[str], path: Path
) -> dict[str, np.ndarray]:
    n_cols = len(header.columns)
    rows: list[list[float]] = []
    for line in data_lines:
        parts = [s for s in re.split(r"[\s,;]+", line) if s]
        if not parts:
            continue
        if len(parts) < n_cols:
            continue
        try:
            row = [float(parts[i]) for i in range(n_cols)]
        except ValueError:
            continue
        rows.append(row)

    if not rows:
        raise GefParseError(f"{path}: no data rows")

    matrix = np.asarray(rows, dtype=np.float64)

    # Replace VOID sentinels with NaN per-column
    for col in header.columns:
        void = header.void_values.get(col.index)
        if void is not None:
            col_arr = matrix[:, col.index - 1]
            matrix[:, col.index - 1] = np.where(
                np.isclose(col_arr, void), np.nan, col_arr
            )

    out: dict[str, np.ndarray] = {}
    for col in header.columns:
        if col.canonical is None:
            continue
        out[col.canonical] = matrix[:, col.index - 1]
    return out
