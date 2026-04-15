"""
Shared types for the AGS4 Rule 1–20 validator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Error severity — AGS4 Rules do not define a formal severity,
    so the validator assigns one per rule family based on how the
    AGS4 v4.1 spec wording graduates 'must' vs 'should'."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass(frozen=True)
class ValidationError:
    """
    A single rule violation.

    Fields:
        rule:     AGS4 rule number (string so Rule 2a / 10a / 11b fit).
        severity: ``Severity`` — ERROR breaks the file, WARNING is
                  advisory.
        message:  human-readable description.
        group:    offending GROUP name when known (e.g. "SCPT").
        heading:  offending HEADING name when known (e.g. "SCPT_QT").
        line:     1-based line number in the raw file when known.
        row_index: 0-based DATA row index within the group when known.
        context:  extra key/value data the test assertions can inspect.
    """

    rule: str
    severity: Severity
    message: str
    group: str = ""
    heading: str = ""
    line: int | None = None
    row_index: int | None = None
    context: dict = field(default_factory=dict)

    def __str__(self) -> str:
        bits = [f"Rule {self.rule}", self.severity.value]
        if self.group:
            bits.append(f"group={self.group}")
        if self.heading:
            bits.append(f"heading={self.heading}")
        if self.line is not None:
            bits.append(f"line={self.line}")
        return " ".join(bits) + f" — {self.message}"
