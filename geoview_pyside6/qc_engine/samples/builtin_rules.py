"""
geoview_pyside6.qc_engine.samples.builtin_rules
================================================
Reference code-first rule definitions using the ``@rule`` decorator.

These samples operate on a trivial ``dict`` target to keep the qc_engine
free of domain imports. Real CPT rules live in ``geoview_cpt.qc_checks``
(Wave 2 A2.6). The shape, however, is identical:

    target → list[QCIssue]

``build_sample_pack()`` assembles these into a :class:`RulePack` that the
test suite can load and execute end-to-end.
"""
from __future__ import annotations

from typing import Any

from geoview_common.qc.common.models import QCIssue

from geoview_pyside6.qc_engine.rules import Rule, RulePack, rule

__all__ = [
    "depth_monotonic",
    "tip_max_reached",
    "spike_detection",
    "build_sample_pack",
]


@rule(
    id="R_depth_monotonic",
    title="Depth must be monotonically increasing",
    severity="critical",
    category="depth_quality",
    epsilon=0.001,
)
def depth_monotonic(target: dict[str, Any]) -> list[QCIssue]:
    """Flag any depth sample that is not strictly greater than its predecessor."""
    depths = target.get("depths") or []
    issues: list[QCIssue] = []
    prev: float | None = None
    for i, d in enumerate(depths):
        if prev is not None and d <= prev + 1e-6:
            issues.append(
                QCIssue(
                    severity="critical",
                    category="depth_quality",
                    description=f"non-monotonic depth at index {i}: {prev} → {d}",
                    location=f"index={i}",
                )
            )
        prev = d
    return issues


@rule(
    id="R_tip_max_reached",
    title="Tip resistance max limit reached (80 MPa)",
    severity="info",
    category="termination_event",
    threshold_mpa=80.0,
)
def tip_max_reached(target: dict[str, Any]) -> list[QCIssue]:
    """Emit an INFO issue whenever tip resistance touches the sensor ceiling."""
    threshold = 80.0
    hits = [i for i, q in enumerate(target.get("qc_mpa") or []) if q >= threshold]
    if not hits:
        return []
    return [
        QCIssue(
            severity="info",
            category="termination_event",
            description=f"tip resistance hit {threshold} MPa at {len(hits)} sample(s)",
            location=f"first_index={hits[0]}",
            suggestion="verify probe refusal vs sensor saturation",
        )
    ]


@rule(
    id="R_spike_detection",
    title="Spike detection (abs delta > 10 MPa)",
    severity="warning",
    category="basic_quality",
    max_delta_mpa=10.0,
)
def spike_detection(target: dict[str, Any]) -> list[QCIssue]:
    """Flag samples whose tip-resistance jump exceeds the configured delta."""
    qc = target.get("qc_mpa") or []
    max_delta = 10.0
    issues: list[QCIssue] = []
    for i in range(1, len(qc)):
        if abs(qc[i] - qc[i - 1]) > max_delta:
            issues.append(
                QCIssue(
                    severity="warning",
                    category="basic_quality",
                    description=f"spike at index {i}: Δ={qc[i] - qc[i - 1]:.2f} MPa",
                    location=f"index={i}",
                )
            )
    return issues


def build_sample_pack() -> RulePack:
    """Assemble the sample pack used by the integration test."""
    return RulePack(
        name="sample_pack",
        version="0.1",
        domain="sample",
        description="qc_engine smoke-test rule pack (dict targets)",
        rules=[depth_monotonic, tip_max_reached, spike_detection],
    )
