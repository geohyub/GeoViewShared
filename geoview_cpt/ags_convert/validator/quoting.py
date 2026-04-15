"""
Rules 5 / 6 — quoting + field-count checks (raw-byte level).
"""
from __future__ import annotations

import csv
import io
from typing import List

from geoview_cpt.ags_convert.validator.types import Severity, ValidationError

__all__ = ["check_rule_5", "check_rule_6"]


def _parse_ags_line(line: str) -> list[str] | None:
    """Use the csv module to parse one AGS4 DATA line into fields. Returns
    None if the line is not a well-formed CSV record."""
    try:
        reader = csv.reader(io.StringIO(line), delimiter=",", quotechar='"')
        rows = list(reader)
    except csv.Error:
        return None
    if not rows:
        return None
    return rows[0]


def check_rule_5(raw: bytes) -> List[ValidationError]:
    """
    Rule 5 — every data field must be enclosed in double quotes, and
    embedded double quotes must be escaped as ``""``.

    Detection strategy: attempt to csv-parse each non-blank line with
    the double-quote quotechar. If the parser raises or the number of
    parsed fields is zero, the quoting is malformed.
    """
    errors: list[ValidationError] = []
    text = raw.decode("utf-8", errors="replace")
    for idx, line in enumerate(text.split("\r\n")):
        if not line.strip():
            continue
        fields = _parse_ags_line(line)
        if fields is None:
            errors.append(
                ValidationError(
                    rule="5",
                    severity=Severity.ERROR,
                    message="malformed field quoting (csv parse failed)",
                    line=idx + 1,
                )
            )
            continue
        # AGS4 requires every field to be quoted — check that the raw
        # line has an even number of unescaped double quotes so that
        # every field opens and closes exactly one pair.
        dq = line.count('"') - 2 * line.count('""')
        if dq % 2 != 0:
            errors.append(
                ValidationError(
                    rule="5",
                    severity=Severity.ERROR,
                    message="odd number of double quotes — field is not properly closed",
                    line=idx + 1,
                )
            )
    return errors


def check_rule_6(raw: bytes) -> List[ValidationError]:
    """
    Rule 6 — every DATA / HEADING / UNIT / TYPE line within a group
    must have the same number of fields as the group's HEADING line.
    """
    errors: list[ValidationError] = []
    text = raw.decode("utf-8", errors="replace")
    heading_count: int | None = None
    group_name = ""
    for idx, line in enumerate(text.split("\r\n")):
        if not line.strip():
            continue
        fields = _parse_ags_line(line)
        if fields is None:
            continue
        rtype = fields[0] if fields else ""
        if rtype == "GROUP":
            heading_count = None
            group_name = fields[1] if len(fields) > 1 else ""
            continue
        if rtype == "HEADING":
            heading_count = len(fields)
            continue
        if rtype in ("UNIT", "TYPE", "DATA"):
            if heading_count is None:
                errors.append(
                    ValidationError(
                        rule="6",
                        severity=Severity.ERROR,
                        message=f"{rtype} row before a HEADING",
                        line=idx + 1,
                        group=group_name,
                    )
                )
                continue
            if len(fields) != heading_count:
                errors.append(
                    ValidationError(
                        rule="6",
                        severity=Severity.ERROR,
                        message=(
                            f"{rtype} row has {len(fields)} fields, "
                            f"HEADING has {heading_count}"
                        ),
                        line=idx + 1,
                        group=group_name,
                    )
                )
    return errors
