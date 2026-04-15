"""
Rules 13 / 14 / 15 / 16 / 17 / 18 — mandatory group coverage.

AGS4 v4.1 §5 requires every file to contain the five file-level
groups (PROJ, TRAN, UNIT, TYPE, DICT) with populated DATA rows. This
module closes Gap #5 by checking data-row counts rather than just
group presence.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

import pandas as pd

from geoview_cpt.ags_convert.validator.types import Severity, ValidationError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = [
    "check_rule_13",
    "check_rule_14",
    "check_rule_15",
    "check_rule_16",
    "check_rule_17",
    "check_rule_18",
]


def _data_row_count(df: pd.DataFrame) -> int:
    return max(0, len(df) - 2)


def _required_group(
    bundle: "AGSBundle",
    rule: str,
    group: str,
    *,
    min_rows: int = 1,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    df = bundle.tables.get(group)
    if df is None:
        errors.append(
            ValidationError(
                rule=rule,
                severity=Severity.ERROR,
                group=group,
                message=f"mandatory group {group!r} missing",
            )
        )
        return errors
    if _data_row_count(df) < min_rows:
        errors.append(
            ValidationError(
                rule=rule,
                severity=Severity.ERROR,
                group=group,
                message=(
                    f"mandatory group {group!r} has "
                    f"{_data_row_count(df)} DATA rows, expected ≥ {min_rows}"
                ),
            )
        )
    return errors


def check_rule_13(bundle: "AGSBundle") -> List[ValidationError]:
    """Rule 13 — PROJ mandatory, exactly one DATA row."""
    errors = _required_group(bundle, "13", "PROJ", min_rows=1)
    df = bundle.tables.get("PROJ")
    if df is not None and _data_row_count(df) > 1:
        errors.append(
            ValidationError(
                rule="13",
                severity=Severity.ERROR,
                group="PROJ",
                message=(
                    f"PROJ must have exactly 1 DATA row, found {_data_row_count(df)}"
                ),
            )
        )
    return errors


def check_rule_14(bundle: "AGSBundle") -> List[ValidationError]:
    """Rule 14 — TRAN mandatory."""
    return _required_group(bundle, "14", "TRAN", min_rows=1)


def check_rule_15(bundle: "AGSBundle") -> List[ValidationError]:
    """Rule 15 — UNIT dictionary mandatory."""
    return _required_group(bundle, "15", "UNIT", min_rows=1)


def check_rule_16(bundle: "AGSBundle") -> List[ValidationError]:
    """Rule 16 — TYPE dictionary mandatory."""
    return _required_group(bundle, "16", "TYPE", min_rows=1)


def check_rule_17(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 17 — every TYPE code used in a GROUP's TYPE row must appear
    in the TYPE dictionary.
    """
    errors: list[ValidationError] = []
    type_df = bundle.tables.get("TYPE")
    if type_df is None:
        return errors  # Rule 16 catches the missing-group case
    declared: set[str] = set()
    if "TYPE_TYPE" in type_df.columns:
        declared = {
            str(v).strip() for v in type_df.iloc[2:]["TYPE_TYPE"] if str(v).strip()
        }
    for group_name, df in bundle.tables.items():
        if group_name in ("UNIT", "TYPE", "DICT"):
            continue
        if len(df) < 2:
            continue
        type_row = df.iloc[1]
        for col in df.columns:
            if col == "HEADING":
                continue
            type_code = str(type_row.get(col, "")).strip()
            if type_code and type_code not in declared:
                errors.append(
                    ValidationError(
                        rule="17",
                        severity=Severity.ERROR,
                        group=group_name,
                        heading=col,
                        message=(
                            f"TYPE {type_code!r} not declared in TYPE dictionary"
                        ),
                    )
                )
    return errors


def check_rule_18(bundle: "AGSBundle") -> List[ValidationError]:
    """Rule 18 — DICT mandatory when user-defined (non-standard)
    groups appear. For the Week 14 scope every group is standard so
    this check is a stub; it still flags an empty DICT group.
    """
    errors: list[ValidationError] = []
    dict_df = bundle.tables.get("DICT")
    if dict_df is not None and _data_row_count(dict_df) == 0:
        errors.append(
            ValidationError(
                rule="18",
                severity=Severity.WARNING,
                group="DICT",
                message="DICT group present but empty",
            )
        )
    return errors
