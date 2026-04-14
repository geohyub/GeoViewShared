"""
geoview_pyside6.qc_engine.rules
================================
Core DSL primitives for the declarative QC rule engine (Phase A-1 A1.2).

Design decisions:
 - **Severity** mirrors `QCIssue.severity` string values ("critical"|"warning"|"info")
   so runner can pass through without translation.
 - **Rule** is a frozen dataclass (immutable — callers cannot mutate id/severity
   after construction; the ``parameters`` dict should still be treated as read-only).
 - **RulePack** is mutable — supports in-place rule assembly — but `filter()` returns
   a new pack so callers can chain without mutating the source.
 - **@rule decorator** converts a plain function into a Rule instance.
   Decorated name is preserved on the Rule via __wrapped__-style metadata
   but returns the Rule itself (not a wrapper function), so the module
   namespace ends up with Rule objects — matching the data-first YAML view.
 - Severity accepts either the enum or a raw string (YAML loader hands raw strings).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

__all__ = [
    "Severity",
    "Rule",
    "RulePack",
    "RuleCheck",
    "RuleAutoFix",
    "rule",
]


class Severity(str, Enum):
    """Issue severity — mirrors QCIssue.severity values."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

    @classmethod
    def coerce(cls, value: "Severity | str") -> "Severity":
        """Accept enum or raw string (case-insensitive)."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return cls(value.lower())
            except ValueError as exc:
                raise ValueError(
                    f"Unknown severity {value!r}; expected one of "
                    f"{[m.value for m in cls]}"
                ) from exc
        raise TypeError(f"Severity must be str or Severity, got {type(value).__name__}")


# Check functions return a list of QCIssue — typed as Any here to keep the
# qc_engine module itself free of geoview_common imports at definition time.
# The runner.py side does the strict type binding.
RuleCheck = Callable[[Any], list]
RuleAutoFix = Callable[[Any], list] | None


@dataclass(frozen=True)
class Rule:
    """
    Declarative QC rule.

    Attributes:
        id:          Stable machine-readable identifier (e.g. "R_depth_monotonic").
        title:       Human-readable summary shown in reports/UI.
        severity:    Severity level driving QCIssue.severity and scoring.
        category:    Free-form grouping key (e.g. "depth_quality", "termination_event").
        check:       Pure function: target -> list[QCIssue]. Raising is allowed —
                     RuleRunner swallows exceptions and converts to a fail issue.
        auto_fix:    Optional hook invoked when runner.run(..., auto_fix=True).
        description: Long-form explanation for docs / tooltips.
        parameters:  Frozen-ish dict of tuning knobs (thresholds, etc.). Kept as dict
                     for ergonomics; treat as read-only.
    """

    id: str
    title: str
    severity: Severity
    category: str
    check: RuleCheck
    auto_fix: RuleAutoFix = None
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Rule.id must not be empty")
        if not self.title:
            raise ValueError("Rule.title must not be empty")
        if not self.category:
            raise ValueError("Rule.category must not be empty")
        if not callable(self.check):
            raise TypeError(f"Rule.check must be callable, got {type(self.check).__name__}")
        if self.auto_fix is not None and not callable(self.auto_fix):
            raise TypeError("Rule.auto_fix must be callable or None")
        # Coerce severity if a raw string slipped in (frozen dataclass → object.__setattr__)
        if not isinstance(self.severity, Severity):
            object.__setattr__(self, "severity", Severity.coerce(self.severity))


@dataclass
class RulePack:
    """
    Collection of rules grouped by domain/version.

    Attributes:
        name:        Pack name (e.g. "cpt_base").
        version:     Pack version string ("1.0").
        domain:      Free-form domain tag ("cpt", "mag", ...). Does NOT need to match
                     QCDomain — packs can be cross-domain.
        rules:       Ordered list of Rule instances. Duplicate ids forbidden.
        description: Long-form description.
    """

    name: str
    version: str
    domain: str
    rules: list[Rule] = field(default_factory=list)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("RulePack.name must not be empty")
        if not self.version:
            raise ValueError("RulePack.version must not be empty")
        if not self.domain:
            raise ValueError("RulePack.domain must not be empty")
        self._check_unique_ids()

    def _check_unique_ids(self) -> None:
        seen: set[str] = set()
        for r in self.rules:
            if r.id in seen:
                raise ValueError(f"RulePack {self.name!r} contains duplicate rule id {r.id!r}")
            seen.add(r.id)

    def get(self, rule_id: str) -> Rule:
        """Return rule by id. Raises KeyError if missing."""
        for r in self.rules:
            if r.id == rule_id:
                return r
        raise KeyError(f"Rule {rule_id!r} not found in pack {self.name!r}")

    def filter(
        self,
        *,
        severity: Severity | str | None = None,
        category: str | None = None,
    ) -> "RulePack":
        """Return a new RulePack restricted by severity and/or category."""
        sev = Severity.coerce(severity) if severity is not None else None
        selected = [
            r
            for r in self.rules
            if (sev is None or r.severity == sev)
            and (category is None or r.category == category)
        ]
        return RulePack(
            name=f"{self.name}:filtered",
            version=self.version,
            domain=self.domain,
            rules=selected,
            description=self.description,
        )

    def add(self, r: Rule) -> None:
        """Append a rule; raises on duplicate id."""
        if any(existing.id == r.id for existing in self.rules):
            raise ValueError(f"Rule id {r.id!r} already present in pack {self.name!r}")
        self.rules.append(r)

    def __len__(self) -> int:
        return len(self.rules)

    def __iter__(self):
        return iter(self.rules)


def rule(
    *,
    id: str,
    title: str,
    severity: Severity | str,
    category: str,
    description: str = "",
    auto_fix: RuleAutoFix = None,
    **parameters: Any,
) -> Callable[[RuleCheck], Rule]:
    """
    Decorator turning a check function into a :class:`Rule`.

    Extra keyword arguments are captured as ``parameters`` — useful for
    threshold-driven checks that want their knobs visible on the Rule::

        @rule(
            id="R_tip_max",
            title="Tip resistance max limit reached",
            severity="info",
            category="termination_event",
            threshold_mpa=80.0,
        )
        def tip_max(target) -> list[QCIssue]:
            ...

    The decorated name is replaced by a Rule object — the original function
    remains accessible via ``Rule.check``.
    """

    def _wrap(fn: RuleCheck) -> Rule:
        if not callable(fn):
            raise TypeError("@rule must decorate a callable")
        return Rule(
            id=id,
            title=title,
            severity=Severity.coerce(severity),
            category=category,
            check=fn,
            auto_fix=auto_fix,
            description=description or (fn.__doc__ or "").strip(),
            parameters=dict(parameters),
        )

    return _wrap
