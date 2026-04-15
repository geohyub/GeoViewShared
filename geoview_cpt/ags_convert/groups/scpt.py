"""
geoview_cpt.ags_convert.groups.scpt
=======================================
SCPG / SCPT / SCPP GROUP writers — AGS4 v4.1.1 compliant.

Week 15 W1–W4 rewrite:

 - **SCPG** one row per sounding, columns limited to the AGS4 v4.1.1
   standard dictionary: ``LOCA_ID`` + ``SCPG_TESN`` KEY, equipment
   (``SCPG_TYPE`` / ``SCPG_METH``), cone geometry (``SCPG_CSA`` —
   cone surface area, ``SCPG_CAR`` — area ratio), remarks
   (``SCPG_REM``).
 - **SCPT** one row per depth sample — ``SCPT_FRR`` is the AGS4
   friction ratio heading (Week 14 writer used ``SCPT_FR`` which is
   W3). KEY is ``(LOCA_ID, SCPG_TESN, SCPT_DPTH)``; SCPG_TESN is
   stamped ``"01"`` when the header does not supply a test number
   (W2 fix).
 - **SCPP** is the AGS4 *parameters* group, **not** a per-depth
   group. One row per stratum layer carries ``(SCPP_TOP, SCPP_BASE,
   SCPP_REF)`` KEY columns plus ``SCPP_CSBT`` (Soil Behaviour Type
   Index from Robertson Ic averaged over the layer). When the
   sounding has no stratigraphy attached the builder returns an
   empty-DATA SCPP so callers can omit it upstream.

The Week 13 legacy column names (``SCPG_CARD`` / ``SCPP_DPTH`` /
``SCPP_IC`` / ``SCPP_NKT`` / ``SCPT_FR``) are gone; the test suite
pins the new names.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import numpy as np
import pandas as pd

from geoview_cpt.ags_convert.groups._helpers import (
    build_table,
    format_decimal,
    safe_text,
)
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from geoview_gi.minimal_model import StratumLayer

__all__ = [
    "DEFAULT_SCPG_TESN",
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


DEFAULT_SCPG_TESN = "01"
"""W2 fix — SCPG_TESN is a KEY column (Rule 10b), so blank is not
allowed. A single-sounding AGS4 file uses test number ``"01"``."""


# ---------------------------------------------------------------------------
# SCPG (general / equipment)
# ---------------------------------------------------------------------------


SCPG_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "SCPG_TESN",
    "SCPG_TYPE",
    "SCPG_METH",
    "SCPG_CSA",
    "SCPG_CAR",
    "SCPG_REM",
)

SCPG_UNITS: tuple[str, ...] = (
    "",
    "",
    "",
    "",
    "",
    "mm2",  # SCPG_CSA — cone surface area (mm²)
    "",     # SCPG_CAR — area ratio (dimensionless)
    "",
)

SCPG_TYPES: tuple[str, ...] = (
    "",
    "ID",
    "X",
    "X",
    "X",
    "2DP",
    "3DP",
    "X",
)


def build_scpg(sounding: CPTSounding) -> pd.DataFrame:
    """Build the single-row SCPG GROUP DataFrame (AGS4 standard cols only)."""
    header = sounding.header
    row = {
        "LOCA_ID":   safe_text(sounding.name),
        "SCPG_TESN": DEFAULT_SCPG_TESN,
        "SCPG_TYPE": "",
        "SCPG_METH": "",
        "SCPG_CSA":  "",
        "SCPG_CAR":  "",
        "SCPG_REM":  "",
    }
    if header is not None:
        row["SCPG_TYPE"] = safe_text(header.equipment_model)
        if header.cone_base_area_mm2:
            row["SCPG_CSA"] = format_decimal(header.cone_base_area_mm2, 2)
        if header.cone_area_ratio_a:
            row["SCPG_CAR"] = format_decimal(header.cone_area_ratio_a, 3)
    return build_table(SCPG_COLUMNS, SCPG_UNITS, SCPG_TYPES, [row])


# ---------------------------------------------------------------------------
# SCPT (per-depth raw + first-pass derived)
# ---------------------------------------------------------------------------


SCPT_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "SCPG_TESN",
    "SCPT_DPTH",
    "SCPT_RES",
    "SCPT_FRES",
    "SCPT_PWP2",
    "SCPT_QT",
    "SCPT_FRR",
    "SCPT_BQ",
)

SCPT_UNITS: tuple[str, ...] = (
    "",
    "",
    "",
    "m",      # SCPT_DPTH
    "MN/m2",  # SCPT_RES  (qc)
    "kN/m2",  # SCPT_FRES (fs)
    "kN/m2",  # SCPT_PWP2 (u2)
    "MN/m2",  # SCPT_QT
    "%",      # SCPT_FRR  (friction ratio — W3 fix, was SCPT_FR)
    "",       # SCPT_BQ
)

SCPT_TYPES: tuple[str, ...] = (
    "",
    "ID",
    "X",
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

    qt / FRR / Bq come from ``sounding.derived`` when available;
    empty when the derivation chain has not been run yet. FRR is the
    AGS4 v4.1.1 heading for friction ratio — our ``derived`` slot
    may be named ``"Fr"`` or ``"Rf"`` for legacy reasons and both
    names are accepted.
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
    loca_id = safe_text(sounding.name)
    rows: list[dict[str, str]] = []
    # Composite KEY dedup: (LOCA_ID, SCPG_TESN, SCPT_DPTH) must be
    # unique per AGS4 Rule 10a. Vendor bundles (JAKO CPT01) are
    # often oversampled relative to the 2DP display precision, so
    # multiple raw samples collapse to the same SCPT_DPTH string.
    # The writer keeps the **first** sample for each unique depth
    # bin — the user can resample to finer depth precision via the
    # A-2 decimation step if they need the high-rate trace.
    seen_depths: set[str] = set()
    for i in range(n):
        depth_str = format_decimal(_at(depth, i), 2)
        if depth_str in seen_depths:
            continue
        seen_depths.add(depth_str)
        row = {
            "LOCA_ID":   loca_id,
            "SCPG_TESN": DEFAULT_SCPG_TESN,
            "SCPT_DPTH": depth_str,
            "SCPT_RES":  format_decimal(_at(qc_mpa, i), 2),
            "SCPT_FRES": format_decimal(_at(fs_kpa, i), 2),
            "SCPT_PWP2": format_decimal(_at(u2_kpa, i), 2),
            "SCPT_QT":   format_decimal(_at(qt_mpa, i), 2),
            "SCPT_FRR":  format_decimal(_at(fr_pct, i), 2),
            "SCPT_BQ":   format_decimal(_at(bq_arr, i), 3),
        }
        rows.append(row)
    return build_table(SCPT_COLUMNS, SCPT_UNITS, SCPT_TYPES, rows)


# ---------------------------------------------------------------------------
# SCPP (per-stratum interpreted parameters)
# ---------------------------------------------------------------------------


SCPP_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "SCPG_TESN",
    "SCPP_TOP",
    "SCPP_BASE",
    "SCPP_REF",
    "SCPP_CSBT",
    "SCPP_REM",
)

SCPP_UNITS: tuple[str, ...] = (
    "",
    "",
    "",
    "m",
    "m",
    "",
    "",    # SCPP_CSBT (Ic — dimensionless)
    "",
)

SCPP_TYPES: tuple[str, ...] = (
    "",
    "ID",
    "X",
    "2DP",
    "2DP",
    "X",
    "3DP",
    "X",
)


def build_scpp(sounding: CPTSounding) -> pd.DataFrame:
    """
    Build the SCPP GROUP DataFrame — one row per stratum layer.

    Source: ``sounding.strata`` populated by
    ``geoview_cpt.stratigraphy.auto_split_by_ic``. Ic from the
    derivation chain is **averaged over each layer** and written as
    ``SCPP_CSBT`` (Soil Behaviour Type Index — the Robertson 2009
    Ic).

    When the sounding has no stratigraphy attached, an empty-DATA
    SCPP is returned (valid AGS4 — still emits the UNIT / TYPE
    rows). The orchestrator omits the group entirely from the
    bundle in that case.
    """
    strata = list(getattr(sounding, "strata", []) or [])
    if not strata:
        return build_table(SCPP_COLUMNS, SCPP_UNITS, SCPP_TYPES, [])

    depth = _channel_array(sounding, "depth", source="raw")
    ic = _channel_array(sounding, "Ic", source="derived")

    loca_id = safe_text(sounding.name)
    rows: list[dict[str, str]] = []
    for idx, layer in enumerate(strata, start=1):
        csbt = _layer_mean(depth, ic, layer.top_m, layer.base_m)
        rows.append(
            {
                "LOCA_ID":   loca_id,
                "SCPG_TESN": DEFAULT_SCPG_TESN,
                "SCPP_TOP":  format_decimal(layer.top_m, 2),
                "SCPP_BASE": format_decimal(layer.base_m, 2),
                "SCPP_REF":  f"L{idx:02d}",
                "SCPP_CSBT": format_decimal(csbt, 3),
                "SCPP_REM":  safe_text(layer.description),
            }
        )
    return build_table(SCPP_COLUMNS, SCPP_UNITS, SCPP_TYPES, rows)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _layer_mean(
    depth: np.ndarray | None,
    values: np.ndarray | None,
    top: float,
    base: float,
) -> float | None:
    if depth is None or values is None or depth.size == 0:
        return None
    mask = (depth >= top) & (depth <= base)
    if not np.any(mask):
        return None
    window = values[mask]
    window = window[np.isfinite(window)]
    if window.size == 0:
        return None
    return float(window.mean())


def _channel_array(
    sounding: CPTSounding,
    name: str,
    *,
    source: str = "raw",
) -> np.ndarray | None:
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
