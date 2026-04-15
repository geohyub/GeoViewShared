"""
Rules 19 / 19a — naming convention checks.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, List

from geoview_cpt.ags_convert.validator.types import Severity, ValidationError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = ["check_rule_19", "check_rule_19a"]


_GROUP_NAME = re.compile(r"^[A-Z][A-Z0-9]{1,3}$")
_HEADING_NAME = re.compile(r"^[A-Z0-9_]{1,10}$")


def check_rule_19(bundle: "AGSBundle") -> List[ValidationError]:
    """Rule 19 — GROUP names are up to 4 uppercase letters/digits."""
    errors: list[ValidationError] = []
    for group_name in bundle.tables.keys():
        if not _GROUP_NAME.match(group_name):
            errors.append(
                ValidationError(
                    rule="19",
                    severity=Severity.ERROR,
                    group=group_name,
                    message=(
                        f"group name {group_name!r} does not match "
                        "/^[A-Z][A-Z0-9]{1,3}$/"
                    ),
                )
            )
    return errors


def check_rule_19a(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Rule 19a — HEADING names follow ``GRP_NAME`` where ``GRP`` is 3–4
    chars and ``NAME`` is up to 4 chars. The combined string is at
    most 10 characters. Blank cells in the HEADING position are
    allowed (they map to the leading ``HEADING`` column).
    """
    errors: list[ValidationError] = []
    for group_name, df in bundle.tables.items():
        for col in df.columns:
            if col == "HEADING":
                continue
            if not _HEADING_NAME.match(col):
                errors.append(
                    ValidationError(
                        rule="19a",
                        severity=Severity.ERROR,
                        group=group_name,
                        heading=col,
                        message=(
                            f"HEADING name {col!r} does not match "
                            "/^[A-Z0-9_]{1,10}$/"
                        ),
                    )
                )
    return errors
