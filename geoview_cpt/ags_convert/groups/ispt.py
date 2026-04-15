"""
geoview_cpt.ags_convert.groups.ispt
=======================================
ISPT GROUP writer — Standard Penetration Test records, one row per
:class:`SPTTest` instance.

Source: ``borehole.spt_tests`` populated by
``geoview_gi.parsers.in_situ`` or the field-book parser.

Column mapping (AGS4 v4.1.1 DICT):

    LOCA_ID   ← loca_id argument             (ID, KEY)
    ISPT_TOP  ← SPTTest.top_m        (m, 2DP, KEY)
    ISPT_SEAT ← SPTTest.seat_blows           (0DP)
    ISPT_MAIN ← SPTTest.main_blows           (0DP)
    ISPT_NVAL ← SPTTest.n_value              (0DP)
    ISPT_METH ← SPTTest.method               (X)
    ISPT_REM  ← SPTTest.remarks + refusal-tag (X)

The refusal flag is emitted in ``ISPT_REM`` because the AGS4 standard
has no dedicated boolean; ``"REFUSAL"`` is prepended when
``SPTTest.refusal`` is ``True``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import pandas as pd

from geoview_cpt.ags_convert.groups._helpers import (
    build_table,
    format_decimal,
    safe_text,
)

if TYPE_CHECKING:
    from geoview_gi.minimal_model import SPTTest

__all__ = ["ISPT_COLUMNS", "ISPT_UNITS", "ISPT_TYPES", "build_ispt"]


ISPT_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "ISPT_TOP",
    "ISPT_SEAT",
    "ISPT_MAIN",
    "ISPT_NVAL",
    "ISPT_METH",
    "ISPT_REM",
)

ISPT_UNITS: tuple[str, ...] = (
    "",
    "",
    "m",
    "",
    "",
    "",
    "",
    "",
)

ISPT_TYPES: tuple[str, ...] = (
    "",
    "ID",
    "2DP",
    "0DP",
    "0DP",
    "0DP",
    "X",
    "X",
)


def build_ispt(
    loca_id: str,
    spt_tests: "Iterable[SPTTest]",
) -> pd.DataFrame:
    """
    Build the ISPT GROUP DataFrame.

    Args:
        loca_id:   LOCA_ID value (one borehole per call).
        spt_tests: iterable of :class:`SPTTest` — usually
                   ``borehole.spt_tests``.
    """
    loca_id_text = safe_text(loca_id)
    rows: list[dict[str, str]] = []
    for spt in spt_tests:
        rem_bits: list[str] = []
        if spt.refusal:
            rem_bits.append("REFUSAL")
        if spt.remarks:
            rem_bits.append(spt.remarks)
        row = {
            "LOCA_ID":   loca_id_text,
            "ISPT_TOP":  format_decimal(spt.top_m, decimals=2),
            "ISPT_SEAT": _int_or_blank(spt.seat_blows),
            "ISPT_MAIN": _int_or_blank(spt.main_blows),
            "ISPT_NVAL": _int_or_blank(spt.n_value),
            "ISPT_METH": safe_text(spt.method),
            "ISPT_REM":  safe_text(" ".join(rem_bits)),
        }
        rows.append(row)
    return build_table(ISPT_COLUMNS, ISPT_UNITS, ISPT_TYPES, rows)


def _int_or_blank(value: int | None) -> str:
    if value is None:
        return ""
    return str(int(value))
