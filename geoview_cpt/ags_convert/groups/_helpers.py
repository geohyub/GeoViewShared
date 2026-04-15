"""
geoview_cpt.ags_convert.groups._helpers
===========================================
Shared utilities for the per-GROUP AGS4 writers.

Every GROUP DataFrame produced by this package follows the AGS4
row-order contract:

    row 0   UNIT  — per-column unit string ("" for text columns)
    row 1   TYPE  — AGS4 type code ("X", "ID", "DT", "2DP", ...)
    row 2+  DATA  — actual values

The :func:`build_table` helper takes the column order, unit row,
type row, and a list of per-row data dicts and produces a pandas
DataFrame in exactly that shape — so each GROUP writer stays focused
on the domain-specific value extraction and unit choice.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Sequence

import pandas as pd

__all__ = [
    "build_table",
    "format_date_iso",
    "format_decimal",
    "safe_text",
]


def build_table(
    columns: Sequence[str],
    units: Sequence[str],
    types: Sequence[str],
    rows: Iterable[dict[str, Any]],
) -> pd.DataFrame:
    """
    Assemble a GROUP DataFrame in AGS4 row-order.

    Args:
        columns:  full column list **including** ``"HEADING"`` as the
                  first column.
        units:    unit strings in the same order as ``columns`` (the
                  HEADING column itself is ignored — pass ``""`` or
                  whatever).
        types:    AGS4 TYPE codes in the same order.
        rows:     iterable of dicts keyed by column name. Missing keys
                  yield empty strings so the writer can omit values
                  gracefully.

    The returned DataFrame has:
        row 0   HEADING="UNIT", columns filled from ``units``
        row 1   HEADING="TYPE", columns filled from ``types``
        row 2+  HEADING="DATA", columns filled from each input row
    """
    if columns[0] != "HEADING":
        raise ValueError("First column must be 'HEADING'")
    if len(units) != len(columns):
        raise ValueError(
            f"units length {len(units)} != columns length {len(columns)}"
        )
    if len(types) != len(columns):
        raise ValueError(
            f"types length {len(types)} != columns length {len(columns)}"
        )

    unit_row: dict[str, Any] = {"HEADING": "UNIT"}
    type_row: dict[str, Any] = {"HEADING": "TYPE"}
    for col, unit, type_ in zip(columns, units, types):
        if col == "HEADING":
            continue
        unit_row[col] = unit
        type_row[col] = type_

    data_rows: list[dict[str, Any]] = []
    for row in rows:
        out = {"HEADING": "DATA"}
        for col in columns[1:]:
            out[col] = safe_text(row.get(col, ""))
        data_rows.append(out)

    all_rows = [unit_row, type_row, *data_rows]
    df = pd.DataFrame(all_rows, columns=list(columns))
    # Ensure every cell is a string so python-ags4's dump_ags doesn't
    # coerce types differently on load/dump (the library expects str).
    for col in columns:
        df[col] = df[col].astype(str)
    return df


def format_date_iso(value: Any) -> str:
    """Render a Python date/datetime as AGS4 yyyy-mm-dd (blank if None)."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip()
    return str(value)


def format_decimal(value: Any, decimals: int = 2) -> str:
    """
    Render a numeric value to ``decimals`` places, returning "" for
    None / NaN / non-finite.
    """
    if value is None or value == "":
        return ""
    try:
        import math
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return ""
        return f"{f:.{decimals}f}"
    except (TypeError, ValueError):
        return ""


def safe_text(value: Any) -> str:
    """Coerce any Python object to a stripped string, ``None`` → ``""``."""
    if value is None:
        return ""
    s = str(value)
    return s.strip()
