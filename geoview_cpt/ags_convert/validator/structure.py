"""
Rules 1 / 2 / 2a / 2b / 3 — file structure checks.

All four rules work on the raw file bytes so they can catch encoding
and line-ending issues before the parser has a chance to normalize
them away.
"""
from __future__ import annotations

from typing import List

from geoview_cpt.ags_convert.validator.types import Severity, ValidationError

__all__ = [
    "check_rule_1",
    "check_rule_2",
    "check_rule_2a",
    "check_rule_2b",
    "check_rule_3",
]


_VALID_RECORD_TYPES = {'"GROUP"', '"HEADING"', '"UNIT"', '"TYPE"', '"DATA"'}


def check_rule_1(raw: bytes) -> List[ValidationError]:
    """Rule 1 — file must be plain text (UTF-8, no BOM)."""
    errors: list[ValidationError] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append(
            ValidationError(
                rule="1",
                severity=Severity.ERROR,
                message="file starts with a UTF-8 BOM (AGS4 Rule 1 forbids BOM)",
            )
        )
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        errors.append(
            ValidationError(
                rule="1",
                severity=Severity.ERROR,
                message=f"file is not valid UTF-8: {exc}",
            )
        )
    return errors


def check_rule_2(raw: bytes) -> List[ValidationError]:
    """Rule 2 — every line must end with CRLF."""
    errors: list[ValidationError] = []
    if not raw:
        return errors
    # Find any LF not preceded by CR
    for i, byte in enumerate(raw):
        if byte == 0x0A and (i == 0 or raw[i - 1] != 0x0D):
            line_no = raw[:i].count(b"\n") + 1
            errors.append(
                ValidationError(
                    rule="2",
                    severity=Severity.ERROR,
                    message="bare LF found — AGS4 Rule 2 requires CRLF line endings",
                    line=line_no,
                )
            )
            break  # first violation is enough
    return errors


def check_rule_2a(raw: bytes) -> List[ValidationError]:
    """Rule 2a — groups must be separated by a blank line."""
    errors: list[ValidationError] = []
    text = raw.decode("utf-8", errors="replace")
    lines = text.split("\r\n")
    prev_was_data = False
    prev_was_blank = True  # start of file counts as blank
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('"GROUP"'):
            if prev_was_data and not prev_was_blank:
                errors.append(
                    ValidationError(
                        rule="2a",
                        severity=Severity.ERROR,
                        message=(
                            "new GROUP header without a preceding blank line"
                        ),
                        line=idx + 1,
                    )
                )
            prev_was_data = False
            prev_was_blank = False
            continue
        if stripped == "":
            prev_was_blank = True
            prev_was_data = False
            continue
        prev_was_blank = False
        if stripped.startswith('"DATA"'):
            prev_was_data = True
    return errors


def check_rule_2b(raw: bytes, max_length: int = 240) -> List[ValidationError]:
    """Rule 2b — advisory — line length should be ≤ 240 characters."""
    errors: list[ValidationError] = []
    text = raw.decode("utf-8", errors="replace")
    for idx, line in enumerate(text.split("\r\n")):
        if len(line) > max_length:
            errors.append(
                ValidationError(
                    rule="2b",
                    severity=Severity.WARNING,
                    message=f"line exceeds {max_length} characters ({len(line)})",
                    line=idx + 1,
                )
            )
    return errors


def check_rule_3(raw: bytes) -> List[ValidationError]:
    """Rule 3 — the first field of every non-blank line must be one of
    the fixed record types (``GROUP`` / ``HEADING`` / ``UNIT`` /
    ``TYPE`` / ``DATA``)."""
    errors: list[ValidationError] = []
    text = raw.decode("utf-8", errors="replace")
    for idx, line in enumerate(text.split("\r\n")):
        stripped = line.strip()
        if not stripped:
            continue
        # Extract the first quoted field
        if not stripped.startswith('"'):
            errors.append(
                ValidationError(
                    rule="3",
                    severity=Severity.ERROR,
                    message="line does not start with a quoted record type",
                    line=idx + 1,
                )
            )
            continue
        end = stripped.find('"', 1)
        if end == -1:
            errors.append(
                ValidationError(
                    rule="3",
                    severity=Severity.ERROR,
                    message="unterminated quoted record type",
                    line=idx + 1,
                )
            )
            continue
        record_type = stripped[: end + 1]
        if record_type not in _VALID_RECORD_TYPES:
            errors.append(
                ValidationError(
                    rule="3",
                    severity=Severity.ERROR,
                    message=f"unknown record type {record_type!r}",
                    line=idx + 1,
                )
            )
    return errors
