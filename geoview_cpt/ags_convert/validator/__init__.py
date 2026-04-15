"""
geoview_cpt.ags_convert.validator
=====================================
AGS4 v4.1 Rule 1–20 validator — Phase A-3 Week 14 A3.3.

Implements a typed, structured alternative to
``python_ags4.AGS4.check_file`` which is print-only and has several
gaps around Rules 10a, 10c, 13–18 (see
``docs/python_ags4_gaps.md``).

Public API::

    from geoview_cpt.ags_convert.validator import (
        ValidationError,
        Severity,
        validate_file,
        validate_bundle,
    )

    errors = validate_file("marine_cpt.ags")
    for err in errors:
        print(err.rule, err.group, err.heading, err.message)

``validate_file`` runs every rule that needs raw-byte access (Rules
1–6, 20) plus every rule that operates on the
:class:`~geoview_cpt.ags_convert.wrapper.AGSBundle`. ``validate_bundle``
runs the subset that can be enforced from the parsed bundle alone —
useful when the writer is composing a new file in memory and wants
pre-dump validation.

Module layout mirrors the AGS4 spec chapters:

    structure.py       Rules 1 / 2 / 2a / 2b / 3
    quoting.py         Rules 5 / 6
    fields.py          Rules 4 / 7 / 8 / 12
    dictionary.py      Rules 9 / 10 / 10a / 10b
    references.py      Rules 10c / 11 / 11a / 11b / 11c
    required_groups.py Rules 13 / 14 / 15 / 16 / 17 / 18 / 18a
    naming.py          Rules 19 / 19a / 19b
    files.py           Rule 20
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List

from geoview_cpt.ags_convert.validator.types import (
    Severity,
    ValidationError,
)
from geoview_cpt.ags_convert.validator.dictionary import (
    check_rule_9,
    check_rule_10,
    check_rule_10a,
    check_rule_10b,
)
from geoview_cpt.ags_convert.validator.fields import (
    check_rule_7,
    check_rule_8,
    check_rule_12,
)
from geoview_cpt.ags_convert.validator.files import check_rule_20
from geoview_cpt.ags_convert.validator.naming import (
    check_rule_19,
    check_rule_19a,
)
from geoview_cpt.ags_convert.validator.quoting import (
    check_rule_5,
    check_rule_6,
)
from geoview_cpt.ags_convert.validator.references import (
    check_rule_10c,
    check_rule_11,
)
from geoview_cpt.ags_convert.validator.required_groups import (
    check_rule_13,
    check_rule_14,
    check_rule_15,
    check_rule_16,
    check_rule_17,
    check_rule_18,
)
from geoview_cpt.ags_convert.validator.structure import (
    check_rule_1,
    check_rule_2,
    check_rule_2a,
    check_rule_3,
)

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = [
    "Severity",
    "ValidationError",
    "validate_file",
    "validate_bundle",
    # Rule functions, re-exported for targeted testing
    "check_rule_1",
    "check_rule_2",
    "check_rule_2a",
    "check_rule_3",
    "check_rule_5",
    "check_rule_6",
    "check_rule_7",
    "check_rule_8",
    "check_rule_9",
    "check_rule_10",
    "check_rule_10a",
    "check_rule_10b",
    "check_rule_10c",
    "check_rule_11",
    "check_rule_12",
    "check_rule_13",
    "check_rule_14",
    "check_rule_15",
    "check_rule_16",
    "check_rule_17",
    "check_rule_18",
    "check_rule_19",
    "check_rule_19a",
    "check_rule_20",
]


def validate_bundle(bundle: "AGSBundle") -> List[ValidationError]:
    """
    Run every rule that operates on a parsed :class:`AGSBundle`.

    Excludes rules that require raw file bytes (1, 2, 2a, 5, 6, 20) —
    those are in :func:`validate_file`.
    """
    errors: list[ValidationError] = []
    errors.extend(check_rule_7(bundle))
    errors.extend(check_rule_8(bundle))
    errors.extend(check_rule_9(bundle))
    errors.extend(check_rule_10(bundle))
    errors.extend(check_rule_10a(bundle))
    errors.extend(check_rule_10b(bundle))
    errors.extend(check_rule_10c(bundle))
    errors.extend(check_rule_11(bundle))
    errors.extend(check_rule_12(bundle))
    errors.extend(check_rule_13(bundle))
    errors.extend(check_rule_14(bundle))
    errors.extend(check_rule_15(bundle))
    errors.extend(check_rule_16(bundle))
    errors.extend(check_rule_17(bundle))
    errors.extend(check_rule_18(bundle))
    errors.extend(check_rule_19(bundle))
    errors.extend(check_rule_19a(bundle))
    return errors


def validate_file(path: str | Path) -> List[ValidationError]:
    """
    Run the full Rule 1–20 suite against an ``.ags`` file.

    Parses the file once with
    :func:`geoview_cpt.ags_convert.wrapper.load_ags` for the
    bundle-based rules, then runs the byte-level rules against the
    raw file content.
    """
    from geoview_cpt.ags_convert.wrapper import load_ags

    path = Path(path)
    raw = path.read_bytes()

    errors: list[ValidationError] = []
    errors.extend(check_rule_1(raw))
    errors.extend(check_rule_2(raw))
    errors.extend(check_rule_2a(raw))
    errors.extend(check_rule_3(raw))
    errors.extend(check_rule_5(raw))
    errors.extend(check_rule_6(raw))

    try:
        bundle = load_ags(path)
    except Exception as exc:
        errors.append(
            ValidationError(
                rule="load",
                severity=Severity.ERROR,
                message=f"file could not be parsed as AGS4: {exc}",
            )
        )
        return errors

    errors.extend(validate_bundle(bundle))
    errors.extend(check_rule_20(bundle, base_dir=path.parent))
    return errors
