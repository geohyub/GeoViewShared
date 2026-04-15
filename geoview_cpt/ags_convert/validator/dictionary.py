"""
Rules 9 / 10 / 10a / 10b — DICT-driven rules.

Rules 10a and 10b are re-implemented here instead of delegating to
``python_ags4`` because the library has a known composite-KEY gap
(see ``docs/python_ags4_gaps.md`` Gap #3).
"""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Dict, List, Tuple

import pandas as pd

from geoview_cpt.ags_convert.validator.types import Severity, ValidationError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = [
    "check_rule_9",
    "check_rule_10",
    "check_rule_10a",
    "check_rule_10b",
    "standard_dict_headings",
    "standard_dict_key_columns",
]


def _data_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[2:]


@lru_cache(maxsize=1)
def _load_standard_dict() -> pd.DataFrame:
    from python_ags4 import AGS4
    import python_ags4
    import os

    path = os.path.join(
        os.path.dirname(python_ags4.__file__), "Standard_dictionary_v4_1_1.ags"
    )
    tables, _ = AGS4.AGS4_to_dataframe(path)
    return tables["DICT"]


def standard_dict_headings(group: str) -> set[str]:
    """Return the set of HEADING names declared for ``group`` in the
    standard AGS4 v4.1.1 dictionary."""
    dict_df = _load_standard_dict()
    rows = dict_df[dict_df["DICT_GRP"] == group]
    return {str(v).strip() for v in rows["DICT_HDNG"] if str(v).strip()}


def standard_dict_key_columns(group: str) -> list[str]:
    """Return the ordered list of KEY columns for ``group`` (DICT_STAT
    == ``KEY``)."""
    dict_df = _load_standard_dict()
    rows = dict_df[
        (dict_df["DICT_GRP"] == group) & (dict_df["DICT_STAT"] == "KEY")
    ]
    return [str(v).strip() for v in rows["DICT_HDNG"] if str(v).strip()]


def check_rule_9(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 9 — every HEADING in a GROUP must be declared in the DICT
    for that group. HEADINGs not in the standard dict are only flagged
    when the bundle does not supply a user DICT override.
    """
    errors: list[ValidationError] = []
    user_dict: set[tuple[str, str]] = set()
    dict_df = bundle.tables.get("DICT")
    if dict_df is not None and "DICT_GRP" in dict_df.columns:
        for _, row in _data_rows(dict_df).iterrows():
            user_dict.add(
                (str(row["DICT_GRP"]).strip(), str(row["DICT_HDNG"]).strip())
            )

    for group_name, df in bundle.tables.items():
        if group_name in ("UNIT", "TYPE", "DICT"):
            continue
        try:
            std = standard_dict_headings(group_name)
        except Exception:
            std = set()
        if not std and not any(g == group_name for g, _ in user_dict):
            # Unknown group entirely — Rule 9 is advisory here
            continue
        for col in df.columns:
            if col == "HEADING":
                continue
            if col in std:
                continue
            if (group_name, col) in user_dict:
                continue
            errors.append(
                ValidationError(
                    rule="9",
                    severity=Severity.ERROR,
                    group=group_name,
                    heading=col,
                    message=f"HEADING {col!r} not declared in DICT for group {group_name!r}",
                )
            )
    return errors


def check_rule_10(bundle: "AGSBundle") -> List[ValidationError]:
    """Rule 10 — every group that has a KEY in the standard dictionary
    must populate every KEY column."""
    errors: list[ValidationError] = []
    for group_name, df in bundle.tables.items():
        if group_name in ("UNIT", "TYPE", "DICT"):
            continue
        try:
            keys = standard_dict_key_columns(group_name)
        except Exception:
            keys = []
        if not keys:
            continue
        missing_keys = [k for k in keys if k not in df.columns]
        for mk in missing_keys:
            errors.append(
                ValidationError(
                    rule="10",
                    severity=Severity.ERROR,
                    group=group_name,
                    heading=mk,
                    message=f"KEY column {mk!r} missing from group",
                )
            )
    return errors


def check_rule_10a(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 10a — composite KEY uniqueness. Reimplemented here because
    ``python_ags4.AGS4.check_file`` misses duplicate composite keys
    for multi-column KEYs (Gap #3).
    """
    errors: list[ValidationError] = []
    for group_name, df in bundle.tables.items():
        if group_name in ("UNIT", "TYPE", "DICT"):
            continue
        try:
            keys = standard_dict_key_columns(group_name)
        except Exception:
            keys = []
        if not keys:
            continue
        present_keys = [k for k in keys if k in df.columns]
        if not present_keys:
            continue
        seen: Dict[Tuple[str, ...], int] = {}
        for data_idx, row in enumerate(_data_rows(df).itertuples(index=False)):
            row_dict = dict(zip(df.columns, row))
            composite = tuple(
                str(row_dict.get(col, "")).strip() for col in present_keys
            )
            if composite in seen:
                errors.append(
                    ValidationError(
                        rule="10a",
                        severity=Severity.ERROR,
                        group=group_name,
                        row_index=data_idx,
                        context={"key": composite, "duplicate_of": seen[composite]},
                        message=(
                            f"composite KEY {composite!r} duplicates row "
                            f"{seen[composite]}"
                        ),
                    )
                )
            else:
                seen[composite] = data_idx
    return errors


def check_rule_10b(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 10b — KEY columns must not be blank. Gap #3 supplement:
    python-ags4 enforces this only on single-column KEYs.
    """
    errors: list[ValidationError] = []
    for group_name, df in bundle.tables.items():
        if group_name in ("UNIT", "TYPE", "DICT"):
            continue
        try:
            keys = standard_dict_key_columns(group_name)
        except Exception:
            keys = []
        present_keys = [k for k in keys if k in df.columns]
        for data_idx, row in enumerate(_data_rows(df).itertuples(index=False)):
            row_dict = dict(zip(df.columns, row))
            for key_col in present_keys:
                value = str(row_dict.get(key_col, "")).strip()
                if not value:
                    errors.append(
                        ValidationError(
                            rule="10b",
                            severity=Severity.ERROR,
                            group=group_name,
                            heading=key_col,
                            row_index=data_idx,
                            message=f"blank KEY value in {key_col!r}",
                        )
                    )
    return errors
