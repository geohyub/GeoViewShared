"""
geoview_cpt.parsers.csv_cpt
================================
Generic CSV → :class:`CPTSounding` reader — Phase A-2 A2.4.

Wraps :class:`geoview_pyside6.parsers.samples.csv_fallback.CSVFallbackParser`
(the A1.1 reference implementation) and materializes the resulting
:class:`CSVPayload` into the canonical CPT channel shape. No new CSV
parsing logic lives here — only column-name heuristics and unit
normalization.

Accepted header variants (case- and separator-insensitive substring
match):

    depth   → "depth", "test length", "penetration", "pen (m)"
    qc      → "qc", "tip", "cone resistance"
    fs      → "fs", "sleeve", "local friction"
    u2      → "u2", "pore", "u₂"
    incl    → "inclination", "tilt", "incl"

Units are inferred from parenthesised trailers in the header
(``qc (MPa)`` / ``fs (kPa)``) when present. Otherwise the reader
assumes:

    depth → m   (always)
    qc    → MPa (Wave 0 convention)
    fs    → kPa (canonical, no conversion applied)
    u2    → kPa (canonical)
    incl  → deg

When the header declares ``fs (MPa)`` or ``u2 (MPa)`` the reader
converts to kPa at ingest time — parser callers always see the
canonical units.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding
from geoview_pyside6.parsers.samples.csv_fallback import (
    CSVFallbackParser,
    CSVPayload,
)

__all__ = [
    "CptCsvParseError",
    "parse_csv_cpt",
    "detect_csv_cpt",
]


class CptCsvParseError(Exception):
    """Raised when the generic CSV cannot be resolved to a CPTSounding."""


_COL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "depth": ("depth", "test length", "penetration", "pen"),
    "qc":    ("qc", "tip", "cone resistance"),
    "fs":    ("fs", "sleeve", "local friction", "friction"),
    "u2":    ("u2", "u 2", "pore"),
    "incl":  ("inclination", "tilt", "incl"),
}

_UNIT_RE = re.compile(r"\(([^)]+)\)")


def detect_csv_cpt(path: Path | str) -> bool:
    """Return True when the A1.1 CSV parser recognises ``path``."""
    p = Path(path)
    parser = CSVFallbackParser()
    try:
        result = parser.detect(p)
    except Exception:
        return False
    return result is not None and result.confidence >= 0.6


def parse_csv_cpt(path: Path | str) -> CPTSounding:
    """
    Read a generic CSV into a :class:`CPTSounding`.

    Args:
        path: filesystem path to a ``.csv`` / ``.tsv`` / ``.txt``.

    Returns:
        :class:`CPTSounding` with whichever canonical channels the
        header declares. Depth is always required.

    Raises:
        CptCsvParseError: on detection failure, missing depth column,
                          or empty data block.
    """
    p = Path(path)
    parser = CSVFallbackParser()
    detected = parser.detect(p)
    if detected is None:
        raise CptCsvParseError(f"{p}: not recognised as CSV")

    try:
        result = parser.parse(p)
    except Exception as exc:
        raise CptCsvParseError(f"{p}: CSVFallbackParser failed: {exc}") from exc
    payload: CSVPayload = result.payload

    col_map, units = _match_columns(payload.header)
    if "depth" not in col_map:
        raise CptCsvParseError(
            f"{p}: no depth column recognised — header was {payload.header!r}"
        )

    arrays = _read_columns(payload.rows, col_map)
    depth = arrays["depth"]
    if depth.size == 0:
        raise CptCsvParseError(f"{p}: empty data block")

    header = CPTHeader(
        sounding_id=p.stem,
        sounding_type="PCPT",
        max_push_depth_m=float(depth.max()),
    )

    sounding = CPTSounding(
        handle=0,
        element_tag="",
        name=p.stem,
        file_name=p.name,
        input_count=int(depth.size),
        output_count=int(depth.size),
        max_depth_m=float(depth.max()),
    )
    sounding.header = header

    channels: dict[str, CPTChannel] = {
        "depth": CPTChannel(name="depth", unit="m", values=depth),
    }
    for key in ("qc", "fs", "u2", "incl"):
        if key not in arrays:
            continue
        values, unit = _normalize_unit(key, arrays[key], units.get(key))
        channels[key] = CPTChannel(name=key, unit=unit, values=values)

    sounding.channels = channels
    sounding.metadata.update(
        {
            "source_format": "csv_generic",
            "source_path": str(p),
            "csv_encoding": payload.encoding,
            "csv_delimiter": payload.delimiter,
            "csv_header": payload.header,
            "matched_columns": col_map,
        }
    )
    return sounding


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _match_columns(
    header: list[str],
) -> tuple[dict[str, int], dict[str, str]]:
    """
    Return ``({canonical: col_index}, {canonical: raw_unit_string})``.

    The first matching column per canonical name wins; subsequent
    duplicates are ignored.
    """
    col_map: dict[str, int] = {}
    units: dict[str, str] = {}
    for idx, raw in enumerate(header):
        low = raw.strip().lower()
        # Pull a (unit) trailer if present
        unit_match = _UNIT_RE.search(raw)
        unit = unit_match.group(1).strip() if unit_match else ""
        for canonical, tokens in _COL_KEYWORDS.items():
            if canonical in col_map:
                continue
            if any(tok in low for tok in tokens):
                col_map[canonical] = idx
                if unit:
                    units[canonical] = unit
                break
    return col_map, units


def _read_columns(
    rows: list[list[str]],
    col_map: dict[str, int],
) -> dict[str, np.ndarray]:
    out: dict[str, list[float]] = {k: [] for k in col_map}
    depth_idx = col_map["depth"]
    for row in rows:
        if depth_idx >= len(row):
            continue
        try:
            d_val = float(row[depth_idx])
        except (TypeError, ValueError):
            continue
        for key, idx in col_map.items():
            if idx >= len(row):
                out[key].append(np.nan)
                continue
            try:
                out[key].append(float(row[idx]))
            except (TypeError, ValueError):
                out[key].append(np.nan)
    return {k: np.asarray(v, dtype=np.float64) for k, v in out.items()}


def _normalize_unit(
    canonical: str,
    values: np.ndarray,
    declared_unit: str | None,
) -> tuple[np.ndarray, str]:
    """
    Convert ``values`` to the canonical unit for this channel.

    Returns ``(values, unit_label)``. The label is always the canonical
    unit so downstream consumers don't have to care about what the CSV
    said.
    """
    declared = (declared_unit or "").strip().lower()
    if canonical == "qc":
        # qc canonical = MPa
        if declared in ("kpa",):
            return values / 1000.0, "MPa"
        return values, "MPa"
    if canonical in ("fs", "u2"):
        # canonical = kPa
        if declared == "mpa":
            return values * 1000.0, "kPa"
        return values, "kPa"
    if canonical == "incl":
        return values, "deg"
    return values, "m"
