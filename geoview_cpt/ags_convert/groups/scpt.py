"""
geoview_cpt.ags_convert.groups.scpt
=======================================
SCPG / SCPT / SCPP GROUP writers — the heart of the marine CPT AGS4
export.

 - **SCPG** (static cone penetration test, general) — **one** row per
   sounding. Equipment + cone geometry + test timing.
 - **SCPT** (static cone penetration test, depth data) — **one row
   per depth sample**. Raw qc/fs/u₂ plus derived qt/Rf/Bq.
 - **SCPP** (static cone penetration test, derived parameters) —
   **one row per depth sample**. Ic + Nkt bookkeeping.

All three share the ``LOCA_ID`` column so a Kingdom reader can join
back to LOCA. Values flow through :mod:`geoview_cpt.correction.units`
converters so the AGS4 output always carries the canonical unit
strings (``MN/m2`` for MPa, ``kN/m2`` for kPa, ``m`` for depth).
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from geoview_cpt.ags_convert.groups._helpers import (
    build_table,
    format_date_iso,
    format_decimal,
    safe_text,
)
from geoview_cpt.model import CPTSounding

__all__ = [
    "SCPG_COLUMNS",
    "SCPG_UNITS",
    "SCPG_TYPES",
    "SCPT_COLUMNS",
    "SCPT_UNITS",
    "SCPT_TYPES",
    "SCPP_COLUMNS",
    "SCPP_UNITS",
    "SCPP_TYPES",
    "build_scpg",
    "build_scpt",
    "build_scpp",
]


# ---------------------------------------------------------------------------
# SCPG (general / equipment / timing)
# ---------------------------------------------------------------------------


SCPG_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "SCPG_TESN",
    "SCPG_TYPE",
    "SCPG_CREW",
    "SCPG_TESD",
    "SCPG_CARD",
    "SCPG_CAR",
    "SCPG_DTIM",
)

SCPG_UNITS: tuple[str, ...] = (
    "",           # HEADING
    "",           # LOCA_ID
    "",           # SCPG_TESN
    "",           # SCPG_TYPE
    "",           # SCPG_CREW
    "yyyy-mm-dd", # SCPG_TESD
    "mm2",        # SCPG_CARD — cone base area
    "",           # SCPG_CAR  — area ratio (dimensionless)
    "s",          # SCPG_DTIM — total duration
)

SCPG_TYPES: tuple[str, ...] = (
    "",
    "ID",
    "X",
    "X",
    "X",
    "DT",
    "2DP",
    "3DP",
    "2DP",
)


def build_scpg(sounding: CPTSounding) -> pd.DataFrame:
    """Build the single-row SCPG GROUP DataFrame."""
    header = sounding.header

    row = {
        "LOCA_ID":   safe_text(sounding.name),
        "SCPG_TESN": "",
        "SCPG_TYPE": "",
        "SCPG_CREW": "",
        "SCPG_TESD": "",
        "SCPG_CARD": "",
        "SCPG_CAR":  "",
        "SCPG_DTIM": "",
    }
    if header is not None:
        row["SCPG_TYPE"] = safe_text(header.equipment_model)
        if header.started_at is not None:
            row["SCPG_TESD"] = format_date_iso(header.started_at)
        if header.cone_base_area_mm2:
            row["SCPG_CARD"] = format_decimal(header.cone_base_area_mm2, 2)
        if header.cone_area_ratio_a:
            row["SCPG_CAR"] = format_decimal(header.cone_area_ratio_a, 3)
        duration = header.duration_s
        if duration is not None:
            row["SCPG_DTIM"] = format_decimal(duration, 2)
    return build_table(SCPG_COLUMNS, SCPG_UNITS, SCPG_TYPES, [row])


# ---------------------------------------------------------------------------
# SCPT (per-depth raw + first-pass derived)
# ---------------------------------------------------------------------------


SCPT_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "SCPT_DPTH",
    "SCPT_RES",
    "SCPT_FRES",
    "SCPT_PWP2",
    "SCPT_QT",
    "SCPT_FR",
    "SCPT_BQ",
)

SCPT_UNITS: tuple[str, ...] = (
    "",       # HEADING
    "",       # LOCA_ID
    "m",      # SCPT_DPTH
    "MN/m2",  # SCPT_RES  (qc)
    "kN/m2",  # SCPT_FRES (fs)
    "kN/m2",  # SCPT_PWP2 (u2)
    "MN/m2",  # SCPT_QT
    "%",      # SCPT_FR
    "",       # SCPT_BQ
)

SCPT_TYPES: tuple[str, ...] = (
    "",
    "ID",
    "2DP",
    "2DP",
    "2DP",
    "2DP",
    "2DP",
    "2DP",
    "3DP",
)


def build_scpt(sounding: CPTSounding) -> pd.DataFrame:
    """
    Build the SCPT per-depth DataFrame.

    Required channels: ``depth``, ``qc``, ``fs``, ``u2``.

    qt / Fr / Bq come from ``sounding.derived`` when available; empty
    when the derivation chain hasn't been run yet.
    """
    depth = _channel_array(sounding, "depth", source="raw")
    qc_mpa = _channel_mpa(sounding, "qc", source="raw")
    fs_kpa = _channel_kpa(sounding, "fs", source="raw")
    u2_kpa = _channel_kpa(sounding, "u2", source="raw")

    qt_mpa = _channel_mpa(sounding, "qt", source="derived")
    fr_pct = _channel_array(sounding, "Fr", source="derived")
    if fr_pct is None:
        fr_pct = _channel_array(sounding, "Rf", source="derived")
    bq_arr = _channel_array(sounding, "Bq", source="derived")

    n = len(depth) if depth is not None else 0
    rows: list[dict[str, str]] = []
    for i in range(n):
        row = {
            "LOCA_ID":   sounding.name,
            "SCPT_DPTH": format_decimal(_at(depth, i), 2),
            "SCPT_RES":  format_decimal(_at(qc_mpa, i), 2),
            "SCPT_FRES": format_decimal(_at(fs_kpa, i), 2),
            "SCPT_PWP2": format_decimal(_at(u2_kpa, i), 2),
            "SCPT_QT":   format_decimal(_at(qt_mpa, i), 2),
            "SCPT_FR":   format_decimal(_at(fr_pct, i), 2),
            "SCPT_BQ":   format_decimal(_at(bq_arr, i), 3),
        }
        rows.append(row)
    return build_table(SCPT_COLUMNS, SCPT_UNITS, SCPT_TYPES, rows)


# ---------------------------------------------------------------------------
# SCPP (per-depth derived parameters)
# ---------------------------------------------------------------------------


SCPP_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "SCPP_DPTH",
    "SCPP_IC",
    "SCPP_NKT",
)

SCPP_UNITS: tuple[str, ...] = (
    "",
    "",
    "m",
    "",   # Ic dimensionless
    "",   # Nkt dimensionless
)

SCPP_TYPES: tuple[str, ...] = (
    "",
    "ID",
    "2DP",
    "3DP",
    "2DP",
)


def build_scpp(
    sounding: CPTSounding,
    *,
    default_nkt: float = 15.0,
) -> pd.DataFrame:
    """
    Build the SCPP per-depth DataFrame.

    Ic is read from ``sounding.derived['Ic']``. Nkt defaults to Wave 0
    canonical ``15`` unless the caller specifies otherwise (the
    Nkt=30 bound is preserved on the chart stack; AGS4 carries a
    single representative value here).
    """
    depth = _channel_array(sounding, "depth", source="raw")
    ic_arr = _channel_array(sounding, "Ic", source="derived")

    n = len(depth) if depth is not None else 0
    rows: list[dict[str, str]] = []
    for i in range(n):
        row = {
            "LOCA_ID":   sounding.name,
            "SCPP_DPTH": format_decimal(_at(depth, i), 2),
            "SCPP_IC":   format_decimal(_at(ic_arr, i), 3),
            "SCPP_NKT":  format_decimal(default_nkt, 2),
        }
        rows.append(row)
    return build_table(SCPP_COLUMNS, SCPP_UNITS, SCPP_TYPES, rows)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _channel_array(
    sounding: CPTSounding,
    name: str,
    *,
    source: str = "raw",
) -> np.ndarray | None:
    """Read ``name`` from ``sounding.channels`` or ``sounding.derived``."""
    if source == "raw":
        ch = sounding.channels.get(name)
    elif source == "derived":
        ch = sounding.derived.get(name)
    else:
        ch = None
    if ch is None:
        return None
    return np.asarray(ch.values, dtype=np.float64)


def _channel_mpa(
    sounding: CPTSounding,
    name: str,
    *,
    source: str = "raw",
) -> np.ndarray | None:
    """Return ``name`` values converted to MPa."""
    ch_store = sounding.channels if source == "raw" else sounding.derived
    ch = ch_store.get(name)
    if ch is None:
        return None
    arr = np.asarray(ch.values, dtype=np.float64)
    unit = (ch.unit or "").strip()
    if unit in ("MPa", "mpa", "MPA"):
        return arr
    if unit in ("kPa", "kpa", "KPA"):
        return arr / 1000.0
    return arr


def _channel_kpa(
    sounding: CPTSounding,
    name: str,
    *,
    source: str = "raw",
) -> np.ndarray | None:
    ch_store = sounding.channels if source == "raw" else sounding.derived
    ch = ch_store.get(name)
    if ch is None:
        return None
    arr = np.asarray(ch.values, dtype=np.float64)
    unit = (ch.unit or "").strip()
    if unit in ("kPa", "kpa", "KPA"):
        return arr
    if unit in ("MPa", "mpa", "MPA"):
        return arr * 1000.0
    return arr


def _at(arr: np.ndarray | None, idx: int) -> float | None:
    if arr is None or idx >= arr.size:
        return None
    value = arr[idx]
    if not np.isfinite(value):
        return None
    return float(value)
