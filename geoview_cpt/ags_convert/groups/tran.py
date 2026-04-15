"""
geoview_cpt.ags_convert.groups.tran
=======================================
TRAN / UNIT / TYPE GROUP writers.

TRAN carries transmission metadata (issue number, date, producer,
status, description, AGS version, recipient). This writer emits a
single DATA row with reasonable defaults — the caller can override
any field via the ``tran_overrides`` dict.

UNIT and TYPE are the **global dictionaries** at the top of an AGS4
file listing every distinct unit string / type code used anywhere in
the document. :func:`build_unit_dictionary` and
:func:`build_type_dictionary` scan the other GROUP DataFrames and
assemble those dictionaries automatically so the writer doesn't have
to maintain a separate list.
"""
from __future__ import annotations

from datetime import date
from typing import Mapping

import pandas as pd

from geoview_cpt.ags_convert.groups._helpers import build_table, format_date_iso, safe_text

__all__ = [
    "TRAN_COLUMNS",
    "TRAN_UNITS",
    "TRAN_TYPES",
    "UNIT_COLUMNS",
    "UNIT_UNITS",
    "UNIT_TYPES",
    "TYPE_COLUMNS",
    "TYPE_UNITS",
    "TYPE_TYPES",
    "build_tran",
    "build_unit_dictionary",
    "build_type_dictionary",
]


TRAN_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "TRAN_ISNO",
    "TRAN_DATE",
    "TRAN_PROD",
    "TRAN_STAT",
    "TRAN_DESC",
    "TRAN_AGS",
    "TRAN_RECV",
    "TRAN_DLIM",
    "TRAN_RCON",
    "TRAN_REM",
)

TRAN_UNITS: tuple[str, ...] = (
    "",           # HEADING
    "",           # TRAN_ISNO
    "yyyy-mm-dd", # TRAN_DATE
    "",           # TRAN_PROD
    "",           # TRAN_STAT
    "",           # TRAN_DESC
    "",           # TRAN_AGS
    "",           # TRAN_RECV
    "",           # TRAN_DLIM
    "",           # TRAN_RCON
    "",           # TRAN_REM
)

TRAN_TYPES: tuple[str, ...] = (
    "",    # HEADING
    "X",   # TRAN_ISNO
    "DT",  # TRAN_DATE
    "X",   # TRAN_PROD
    "X",   # TRAN_STAT
    "X",   # TRAN_DESC
    "X",   # TRAN_AGS
    "X",   # TRAN_RECV
    "X",   # TRAN_DLIM
    "X",   # TRAN_RCON
    "X",   # TRAN_REM
)


# --- UNIT dictionary ---------------------------------------------------


UNIT_COLUMNS: tuple[str, ...] = ("HEADING", "UNIT_UNIT", "UNIT_DESC")
UNIT_UNITS: tuple[str, ...] = ("", "", "")
UNIT_TYPES: tuple[str, ...] = ("", "X", "X")


# Minimal canonical unit→description map — extended automatically when
# a GROUP writer uses a unit string we don't know yet (description
# falls back to the unit string itself).
UNIT_DESCRIPTIONS: dict[str, str] = {
    "":           "",
    "-":          "dimensionless",
    "m":          "metre",
    "mm":         "millimetre",
    "km":         "kilometre",
    "kPa":        "kilopascal",
    "MPa":        "megapascal",
    "kN/m2":      "kilonewton per square metre",
    "MN/m2":      "meganewton per square metre",
    "kN/m3":      "kilonewton per cubic metre",
    "Mg/m3":      "megagrams per cubic metre",
    "deg":        "degree",
    "%":          "percentage",
    "yyyy-mm-dd": "year-month-day",
    "s":          "second",
    "cm":         "centimetre",
    "mm2":        "square millimetre",
    "mm/s":       "millimetre per second",
    "km/s":       "kilometre per second",
    "m/s":        "metre per second",
}


# --- TYPE dictionary ---------------------------------------------------


TYPE_COLUMNS: tuple[str, ...] = ("HEADING", "TYPE_TYPE", "TYPE_DESC")
TYPE_UNITS: tuple[str, ...] = ("", "", "")
TYPE_TYPES: tuple[str, ...] = ("", "X", "X")


TYPE_DESCRIPTIONS: dict[str, str] = {
    "":     "",
    "ID":   "Unique Identifier",
    "X":    "Text",
    "DT":   "Date Time (ISO 8601:2004)",
    "PA":   "Free Pick List",
    "2DP":  "Value with 2 decimal places",
    "3DP":  "Value with 3 decimal places",
    "4DP":  "Value with 4 decimal places",
    "1SF":  "Value with 1 significant figure",
    "2SF":  "Value with 2 significant figures",
    "3SF":  "Value with 3 significant figures",
    "4SF":  "Value with 4 significant figures",
    "2SCI": "Scientific notation with 2 decimal places",
    "YN":   "Yes or No",
    "XN":   "Text/Numeric",
}


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def build_tran(
    *,
    issue_no: str = "1",
    tran_date: date | str | None = None,
    producer: str = "geoview_cpt A3.2",
    status: str = "DRAFT",
    description: str = "",
    recipient: str = "",
    overrides: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """
    Build the TRAN (transmission) GROUP DataFrame.

    Args:
        issue_no:     TRAN_ISNO value. Starts at ``"1"`` for a fresh file.
        tran_date:    TRAN_DATE value. Defaults to today.
        producer:     TRAN_PROD — our tool identifier.
        status:       TRAN_STAT — DRAFT / FINAL / PRELIMINARY / REISSUED.
        description:  TRAN_DESC — free-form file description.
        recipient:    TRAN_RECV — client or destination.
        overrides:    Per-field dict; values replace the defaults above.

    ``TRAN_DLIM`` is fixed at ``"`` (AGS4 double-quote delimiter) and
    ``TRAN_RCON`` at ``,`` to match what python-ags4 emits at dump
    time. These are the AGS4 v4.1 December 2020 defaults and should
    not be changed without re-verifying the byte-level round-trip.
    """
    row: dict[str, str] = {
        "TRAN_ISNO": safe_text(issue_no),
        "TRAN_DATE": format_date_iso(tran_date or date.today()),
        "TRAN_PROD": safe_text(producer),
        "TRAN_STAT": safe_text(status),
        "TRAN_DESC": safe_text(description),
        "TRAN_AGS":  "4.1",
        "TRAN_RECV": safe_text(recipient),
        "TRAN_DLIM": '"',
        "TRAN_RCON": ",",
        "TRAN_REM":  "",
    }
    if overrides:
        for key, value in overrides.items():
            if key in row:
                row[key] = safe_text(value)
    return build_table(TRAN_COLUMNS, TRAN_UNITS, TRAN_TYPES, [row])


def build_unit_dictionary(used_units: set[str]) -> pd.DataFrame:
    """
    Assemble the global UNIT dictionary from a set of unit strings
    collected across every populated GROUP.

    Unknown units get their literal unit string as the description
    so the output is always valid AGS4 even for vendor-specific
    unit spellings.
    """
    cleaned = {u for u in used_units if u}
    rows = [
        {"UNIT_UNIT": u, "UNIT_DESC": UNIT_DESCRIPTIONS.get(u, u)}
        for u in sorted(cleaned)
    ]
    return build_table(UNIT_COLUMNS, UNIT_UNITS, UNIT_TYPES, rows)


def build_type_dictionary(used_types: set[str]) -> pd.DataFrame:
    """
    Assemble the global TYPE dictionary from a set of TYPE codes
    collected across every populated GROUP.
    """
    cleaned = {t for t in used_types if t}
    rows = [
        {"TYPE_TYPE": t, "TYPE_DESC": TYPE_DESCRIPTIONS.get(t, t)}
        for t in sorted(cleaned)
    ]
    return build_table(TYPE_COLUMNS, TYPE_UNITS, TYPE_TYPES, rows)
