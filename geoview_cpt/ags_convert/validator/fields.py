"""
Rules 4 / 7 / 8 / 12 — per-field checks run on the parsed bundle.

Rule 4 (comma delimiter) is enforced by Rules 3 / 6 at the quoting /
field-count level — no separate check needed on the bundle side.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, List

import pandas as pd

from geoview_cpt.ags_convert.validator.types import Severity, ValidationError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = ["check_rule_7", "check_rule_8", "check_rule_12"]


_INT_TYPES = {"0DP"}
_FLOAT_TYPES = {"1DP", "2DP", "3DP", "4DP", "5DP", "6DP"}
_DATE_TYPES = {"DT"}
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$")


def _data_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[2:]


def check_rule_7(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 7 — HEADING / UNIT / TYPE rows must precede DATA rows in a
    group. Because the wrapper always stores them in that order, the
    check verifies the invariant holds after parsing.
    """
    errors: list[ValidationError] = []
    for group_name, df in bundle.tables.items():
        if len(df) < 2:
            errors.append(
                ValidationError(
                    rule="7",
                    severity=Severity.ERROR,
                    group=group_name,
                    message="group has fewer than UNIT + TYPE rows",
                )
            )
            continue
        if df.iloc[0].get("HEADING", "") != "UNIT":
            errors.append(
                ValidationError(
                    rule="7",
                    severity=Severity.ERROR,
                    group=group_name,
                    message="first row is not UNIT",
                )
            )
        if df.iloc[1].get("HEADING", "") != "TYPE":
            errors.append(
                ValidationError(
                    rule="7",
                    severity=Severity.ERROR,
                    group=group_name,
                    message="second row is not TYPE",
                )
            )
        # Make sure every subsequent row is DATA
        for idx in range(2, len(df)):
            if df.iloc[idx].get("HEADING", "") != "DATA":
                errors.append(
                    ValidationError(
                        rule="7",
                        severity=Severity.ERROR,
                        group=group_name,
                        row_index=idx - 2,
                        message=(
                            f"row {idx} has HEADING="
                            f"{df.iloc[idx].get('HEADING', '')!r}, expected DATA"
                        ),
                    )
                )
                break
    return errors


def check_rule_8(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 8 — DATA cell values must conform to the column TYPE code.

    Supports the common AGS4 types only (``ID`` / ``X`` / ``PA`` text
    columns are always valid, numeric ``0DP``/``2DP``/``3DP`` must be
    parseable as numbers, ``DT`` must be ISO-8601 yyyy-mm-dd). Custom
    types (``1SF`` / ``2SCI`` / ``YN`` / ``XN``) are accepted as text
    because the standard dictionary itself does not enforce stricter
    parsing.
    """
    errors: list[ValidationError] = []
    for group_name, df in bundle.tables.items():
        if len(df) < 2:
            continue
        type_row = df.iloc[1]
        headings = [c for c in df.columns if c != "HEADING"]
        for data_idx, row in enumerate(_data_rows(df).itertuples(index=False)):
            row_dict = dict(zip(df.columns, row))
            for col in headings:
                type_code = str(type_row.get(col, "")).strip()
                value = str(row_dict.get(col, "")).strip()
                if not value:
                    continue  # blanks are allowed per Rule 8
                if type_code in _INT_TYPES or type_code in _FLOAT_TYPES:
                    try:
                        float(value)
                    except ValueError:
                        errors.append(
                            ValidationError(
                                rule="8",
                                severity=Severity.ERROR,
                                group=group_name,
                                heading=col,
                                row_index=data_idx,
                                message=(
                                    f"value {value!r} is not a number but column "
                                    f"TYPE is {type_code!r}"
                                ),
                            )
                        )
                elif type_code in _DATE_TYPES:
                    if not _ISO_DATE.match(value):
                        errors.append(
                            ValidationError(
                                rule="8",
                                severity=Severity.ERROR,
                                group=group_name,
                                heading=col,
                                row_index=data_idx,
                                message=(
                                    f"value {value!r} is not ISO-8601 yyyy-mm-dd"
                                ),
                            )
                        )
    return errors


def check_rule_12(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 12 — every distinct UNIT string used in a GROUP's UNIT row
    must appear in the UNIT dictionary (UNIT group DATA rows).
    """
    errors: list[ValidationError] = []
    unit_df = bundle.tables.get("UNIT")
    if unit_df is None:
        return errors  # Rule 15 handles the missing-group case
    declared = set(_data_rows(unit_df)["UNIT_UNIT"]) if "UNIT_UNIT" in unit_df.columns else set()
    declared.discard("")

    for group_name, df in bundle.tables.items():
        if group_name in ("UNIT", "TYPE"):
            continue
        if df.empty:
            continue
        unit_row = df.iloc[0]
        for col in df.columns:
            if col == "HEADING":
                continue
            unit = str(unit_row.get(col, "")).strip()
            if unit and unit not in declared:
                errors.append(
                    ValidationError(
                        rule="12",
                        severity=Severity.ERROR,
                        group=group_name,
                        heading=col,
                        message=(
                            f"unit {unit!r} not present in UNIT dictionary"
                        ),
                    )
                )
    return errors
