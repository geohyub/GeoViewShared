"""
Rules 10c / 11 — parent-group reference integrity.

Rule 10c is reimplemented here (not delegated to python-ags4) — see
``docs/python_ags4_gaps.md`` Gap #4. The standard library coverage
misses SCPT → LOCA and any user-defined parent relationships
declared via DICT_PGRP.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

import pandas as pd

from geoview_cpt.ags_convert.validator.dictionary import (
    standard_dict_key_columns,
)
from geoview_cpt.ags_convert.validator.types import Severity, ValidationError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = ["check_rule_10c", "check_rule_11"]


# Parent-child relationships hardcoded to work around
# python-ags4's incomplete DICT_PGRP coverage (Gap #4).
_PARENT_LINKS: dict[str, tuple[str, str]] = {
    # child_group: (parent_group, shared_key_column)
    "GEOL": ("LOCA", "LOCA_ID"),
    "SAMP": ("LOCA", "LOCA_ID"),
    "ISPT": ("LOCA", "LOCA_ID"),
    "SCPG": ("LOCA", "LOCA_ID"),
    "SCPT": ("LOCA", "LOCA_ID"),
    "SCPP": ("LOCA", "LOCA_ID"),
    "CMPG": ("LOCA", "LOCA_ID"),
    "CMPT": ("LOCA", "LOCA_ID"),
    "IPRM": ("LOCA", "LOCA_ID"),
    "IVAN": ("LOCA", "LOCA_ID"),
    "HDPH": ("LOCA", "LOCA_ID"),
}


def _data_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[2:]


def check_rule_10c(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 10c — every value of a reference column in a child GROUP
    must exist in the parent GROUP's KEY column.
    """
    errors: list[ValidationError] = []
    for child, (parent, fk) in _PARENT_LINKS.items():
        child_df = bundle.tables.get(child)
        parent_df = bundle.tables.get(parent)
        if child_df is None or parent_df is None:
            continue
        if fk not in child_df.columns or fk not in parent_df.columns:
            continue
        parent_keys = {
            str(v).strip() for v in _data_rows(parent_df)[fk] if str(v).strip()
        }
        for data_idx, row in enumerate(_data_rows(child_df).itertuples(index=False)):
            row_dict = dict(zip(child_df.columns, row))
            value = str(row_dict.get(fk, "")).strip()
            if not value:
                continue
            if value not in parent_keys:
                errors.append(
                    ValidationError(
                        rule="10c",
                        severity=Severity.ERROR,
                        group=child,
                        heading=fk,
                        row_index=data_idx,
                        context={"parent": parent, "value": value},
                        message=(
                            f"{fk}={value!r} does not exist in parent group {parent}"
                        ),
                    )
                )
    return errors


def check_rule_11(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 11 — when a group declares a LOCA reference it must carry
    LOCA_ID as a heading. This is the baseline check; Rule 10c above
    handles value integrity.
    """
    errors: list[ValidationError] = []
    for child, (parent, fk) in _PARENT_LINKS.items():
        df = bundle.tables.get(child)
        if df is None:
            continue
        if fk not in df.columns:
            errors.append(
                ValidationError(
                    rule="11",
                    severity=Severity.ERROR,
                    group=child,
                    heading=fk,
                    message=(
                        f"child group {child!r} missing parent reference {fk!r}"
                    ),
                )
            )
    return errors
