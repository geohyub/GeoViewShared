"""
Rule 20 — ``FILE_FSET`` external file references.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

import pandas as pd

from geoview_cpt.ags_convert.validator.types import Severity, ValidationError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = ["check_rule_20"]


def check_rule_20(
    bundle: "AGSBundle",
    *,
    base_dir: Path | None = None,
) -> List[ValidationError]:
    """
    Rule 20 — every ``FILE_FSET`` reference must exist on disk
    relative to the AGS4 file's directory. When ``base_dir`` is
    ``None`` the check is a no-op (round-trip of an in-memory
    bundle).
    """
    errors: list[ValidationError] = []
    if base_dir is None:
        return errors

    for group_name, df in bundle.tables.items():
        if "FILE_FSET" not in df.columns:
            continue
        for data_idx, row in enumerate(df.iloc[2:].itertuples(index=False)):
            row_dict = dict(zip(df.columns, row))
            ref = str(row_dict.get("FILE_FSET", "")).strip()
            if not ref:
                continue
            candidate = base_dir / ref
            if not candidate.exists():
                errors.append(
                    ValidationError(
                        rule="20",
                        severity=Severity.ERROR,
                        group=group_name,
                        heading="FILE_FSET",
                        row_index=data_idx,
                        context={"path": str(candidate)},
                        message=(
                            f"FILE_FSET reference {ref!r} not found on disk"
                        ),
                    )
                )
    return errors
