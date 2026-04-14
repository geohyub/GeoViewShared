"""
geoview_cpt.qc_rules.checks
================================
Fourteen CPT QC check functions referenced by :file:`cpt_base.yaml`.

Each check has the signature ``fn(target: CPTSounding) -> list[QCIssue]``
per the A1.2 RulePack contract. Thresholds are hard-coded here so the
YAML stays declarative — tuning happens by editing constants in this
module (A2.6 v1) with parameter injection a future enhancement
(tracked as open question Q37).

Checks are grouped into three Wave 0 categories:

    basic_quality (5)   depth_monotonic · spike_detection · sensor_saturation
                        · u2_response · inclination_exceed
    termination   (4)   tip_max_reached · sleeve_max_reached · pore_max_reached
                        · penetration_per_push
    drift         (5)   drift_tip_class1 · drift_sleeve_class1 · drift_pore_class1
                        · drift_drill_string_class1 · class_downgrade

Drift checks require acquisition events (``CPTHeader.events``) from the
A2.0 reader. When events are absent they return a single ``info`` issue
noting the data gap rather than a failure — an A2.0b follow-up will
populate ``events`` and flip the drift checks into real comparisons.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from geoview_common.qc.common.models import QCIssue
from geoview_cpt.model import CPTSounding

__all__ = [
    "CHECK_REGISTRY",
    "depth_monotonic",
    "spike_detection",
    "sensor_saturation",
    "u2_response",
    "inclination_exceed",
    "tip_max_reached",
    "sleeve_max_reached",
    "pore_max_reached",
    "penetration_per_push",
    "drift_tip_class1",
    "drift_sleeve_class1",
    "drift_pore_class1",
    "drift_drill_string_class1",
    "class_downgrade",
]


# ---------------------------------------------------------------------------
# Thresholds — ISO 22476-1:2012 Class 1 defaults (Wave 0 catalog §4)
# ---------------------------------------------------------------------------

# Sensor saturation ceilings
TIP_MAX_MPA: float = 80.0
SLEEVE_MAX_KPA: float = 800.0
PORE_MAX_KPA: float = 4000.0

# Spike detection — adjacent-sample tip delta
SPIKE_DELTA_MPA: float = 5.0

# u2 response — minimum std-dev of u2 across the sounding (kPa)
U2_STD_FLOOR_KPA: float = 0.5

# Inclination — ISO 22476-1 Class 1 vertical limit (degrees)
INCLINATION_MAX_DEG: float = 2.0

# Penetration per push (max metres per continuous push segment)
MAX_PUSH_LENGTH_M: float = 3.0

# Drift — Class 1 acceptable zero-return on return stroke (kPa / deg)
DRIFT_TIP_KPA: float = 35.0
DRIFT_SLEEVE_KPA: float = 5.0
DRIFT_PORE_KPA: float = 25.0


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _qc_mpa(target: CPTSounding) -> np.ndarray | None:
    ch = target.channels.get("qc")
    if ch is None or ch.values.size == 0:
        return None
    if ch.unit in {"MPa", "mpa"}:
        return ch.values
    if ch.unit in {"kPa", "kpa"}:
        return ch.values / 1000.0
    return None


def _to_kpa(target: CPTSounding, name: str) -> np.ndarray | None:
    ch = target.channels.get(name)
    if ch is None or ch.values.size == 0:
        return None
    if ch.unit in {"kPa", "kpa"}:
        return ch.values
    if ch.unit in {"MPa", "mpa"}:
        return ch.values * 1000.0
    return None


def _depth(target: CPTSounding) -> np.ndarray | None:
    ch = target.channels.get("depth")
    return ch.values if ch is not None and ch.values.size > 0 else None


def _issue(
    severity: str,
    category: str,
    description: str,
    *,
    location: str = "",
    suggestion: str = "",
) -> QCIssue:
    return QCIssue(
        severity=severity,
        category=category,
        description=description,
        location=location,
        suggestion=suggestion,
    )


def _missing_channel(category: str, name: str) -> QCIssue:
    return _issue(
        "info",
        category,
        f"channel {name!r} missing or empty — check skipped",
        location=name,
    )


def _missing_events(category: str, rule_id: str) -> QCIssue:
    return _issue(
        "info",
        category,
        f"{rule_id}: CPTHeader.events empty — drift check requires "
        f"A2.0b acquisition-event parser",
        suggestion="populate header.events before running drift rules",
    )


# ---------------------------------------------------------------------------
# basic_quality
# ---------------------------------------------------------------------------


def depth_monotonic(target: CPTSounding) -> list[QCIssue]:
    """Depth samples must be non-decreasing. Critical when violated."""
    depth = _depth(target)
    if depth is None:
        return [_missing_channel("basic_quality", "depth")]
    diffs = np.diff(depth)
    bad = np.where(diffs < -1e-6)[0]
    issues: list[QCIssue] = []
    for idx in bad[:10]:  # cap to first 10
        issues.append(
            _issue(
                "critical",
                "basic_quality",
                f"depth decreases at sample {idx}: "
                f"{depth[idx]:.3f} → {depth[idx + 1]:.3f}",
                location=f"index={idx}",
                suggestion="investigate retract event or sensor glitch",
            )
        )
    return issues


def spike_detection(target: CPTSounding) -> list[QCIssue]:
    """Flag adjacent tip-resistance deltas larger than SPIKE_DELTA_MPA."""
    qc = _qc_mpa(target)
    if qc is None:
        return [_missing_channel("basic_quality", "qc")]
    if qc.size < 2:
        return []
    deltas = np.abs(np.diff(qc))
    bad = np.where(deltas > SPIKE_DELTA_MPA)[0]
    issues: list[QCIssue] = []
    for idx in bad[:20]:
        issues.append(
            _issue(
                "warning",
                "basic_quality",
                f"qc spike at sample {idx}: "
                f"Δ={deltas[idx]:.2f} MPa (> {SPIKE_DELTA_MPA} MPa)",
                location=f"index={idx}",
            )
        )
    return issues


def sensor_saturation(target: CPTSounding) -> list[QCIssue]:
    """Detect samples pinned to the vendor-declared sensor ceiling."""
    issues: list[QCIssue] = []
    qc = _qc_mpa(target)
    if qc is not None:
        n = int(np.count_nonzero(qc >= TIP_MAX_MPA))
        if n > 0:
            issues.append(
                _issue(
                    "warning",
                    "basic_quality",
                    f"qc saturated at ≥ {TIP_MAX_MPA} MPa on {n} samples",
                    location="qc",
                )
            )
    fs = _to_kpa(target, "fs")
    if fs is not None:
        n = int(np.count_nonzero(fs >= SLEEVE_MAX_KPA))
        if n > 0:
            issues.append(
                _issue(
                    "warning",
                    "basic_quality",
                    f"fs saturated at ≥ {SLEEVE_MAX_KPA} kPa on {n} samples",
                    location="fs",
                )
            )
    u2 = _to_kpa(target, "u2")
    if u2 is not None:
        n = int(np.count_nonzero(u2 >= PORE_MAX_KPA))
        if n > 0:
            issues.append(
                _issue(
                    "warning",
                    "basic_quality",
                    f"u2 saturated at ≥ {PORE_MAX_KPA} kPa on {n} samples",
                    location="u2",
                )
            )
    return issues


def u2_response(target: CPTSounding) -> list[QCIssue]:
    """Flat u2 (σ ≤ U2_STD_FLOOR_KPA) indicates dead / air-locked transducer."""
    u2 = _to_kpa(target, "u2")
    if u2 is None:
        return [_missing_channel("basic_quality", "u2")]
    if u2.size < 10:
        return []
    std = float(np.std(u2))
    if std < U2_STD_FLOOR_KPA:
        return [
            _issue(
                "warning",
                "basic_quality",
                f"u2 shows no variation (σ={std:.3f} kPa < {U2_STD_FLOOR_KPA})",
                location="u2",
                suggestion="verify pore sensor de-airing before push",
            )
        ]
    return []


def inclination_exceed(target: CPTSounding) -> list[QCIssue]:
    """ISO 22476-1 Class 1 allows ≤ INCLINATION_MAX_DEG from vertical."""
    incl = target.channels.get("incl")
    if incl is None or incl.values.size == 0:
        return [_missing_channel("basic_quality", "incl")]
    peak = float(np.max(np.abs(incl.values)))
    if peak > INCLINATION_MAX_DEG:
        return [
            _issue(
                "warning",
                "basic_quality",
                f"max |inclination| {peak:.2f}° > {INCLINATION_MAX_DEG}° "
                f"(ISO 22476-1 Class 1)",
                location="incl",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# termination
# ---------------------------------------------------------------------------


def tip_max_reached(target: CPTSounding) -> list[QCIssue]:
    """Emit info when the tip limit is hit — typical refusal event."""
    qc = _qc_mpa(target)
    if qc is None:
        return [_missing_channel("termination_event", "qc")]
    hits = int(np.count_nonzero(qc >= TIP_MAX_MPA))
    if hits == 0:
        return []
    return [
        _issue(
            "info",
            "termination_event",
            f"tip resistance ceiling {TIP_MAX_MPA} MPa reached at {hits} sample(s)",
            location="qc",
            suggestion="verify cone refusal vs sensor saturation",
        )
    ]


def sleeve_max_reached(target: CPTSounding) -> list[QCIssue]:
    fs = _to_kpa(target, "fs")
    if fs is None:
        return [_missing_channel("termination_event", "fs")]
    hits = int(np.count_nonzero(fs >= SLEEVE_MAX_KPA))
    if hits == 0:
        return []
    return [
        _issue(
            "info",
            "termination_event",
            f"sleeve friction ceiling {SLEEVE_MAX_KPA} kPa reached at {hits} sample(s)",
            location="fs",
        )
    ]


def pore_max_reached(target: CPTSounding) -> list[QCIssue]:
    u2 = _to_kpa(target, "u2")
    if u2 is None:
        return [_missing_channel("termination_event", "u2")]
    hits = int(np.count_nonzero(u2 >= PORE_MAX_KPA))
    if hits == 0:
        return []
    return [
        _issue(
            "info",
            "termination_event",
            f"pore pressure ceiling {PORE_MAX_KPA} kPa reached at {hits} sample(s)",
            location="u2",
        )
    ]


def penetration_per_push(target: CPTSounding) -> list[QCIssue]:
    """
    Total penetration must not exceed MAX_PUSH_LENGTH_M per continuous
    push. Without acquisition events we only check the overall sounding
    depth as a best-effort bound.
    """
    depth = _depth(target)
    if depth is None:
        return [_missing_channel("termination_event", "depth")]
    total = float(depth.max() - depth.min())
    if total > MAX_PUSH_LENGTH_M * 50:  # 50 pushes before crying wolf
        return [
            _issue(
                "info",
                "termination_event",
                f"total push length {total:.1f} m — review push segmentation "
                f"(A2.0b events needed for per-push accounting)",
                location="depth",
            )
        ]
    return []


# ---------------------------------------------------------------------------
# drift  (event-dependent — stubbed until A2.0b populates header.events)
# ---------------------------------------------------------------------------


def _events(target: CPTSounding):
    if target.header is None:
        return []
    return list(target.header.events or [])


def drift_tip_class1(target: CPTSounding) -> list[QCIssue]:
    if not _events(target):
        return [_missing_events("drift", "R_drift_tip_class1")]
    # Real comparison lands with A2.0b event parser
    return []


def drift_sleeve_class1(target: CPTSounding) -> list[QCIssue]:
    if not _events(target):
        return [_missing_events("drift", "R_drift_sleeve_class1")]
    return []


def drift_pore_class1(target: CPTSounding) -> list[QCIssue]:
    if not _events(target):
        return [_missing_events("drift", "R_drift_pore_class1")]
    return []


def drift_drill_string_class1(target: CPTSounding) -> list[QCIssue]:
    if not _events(target):
        return [_missing_events("drift", "R_drift_drill_string_class1")]
    return []


def class_downgrade(target: CPTSounding) -> list[QCIssue]:
    """
    Aggregate downgrade indicator: if any drift rule would fail we flag
    the sounding as potentially below Class 1. For v1 (no events) this
    simply reports that the class evaluation is pending.
    """
    if not _events(target):
        return [_missing_events("drift", "R_class_downgrade")]
    return []


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


CHECK_REGISTRY: dict[str, Callable[[CPTSounding], list[QCIssue]]] = {
    "depth_monotonic":            depth_monotonic,
    "spike_detection":            spike_detection,
    "sensor_saturation":          sensor_saturation,
    "u2_response":                u2_response,
    "inclination_exceed":         inclination_exceed,
    "tip_max_reached":            tip_max_reached,
    "sleeve_max_reached":         sleeve_max_reached,
    "pore_max_reached":           pore_max_reached,
    "penetration_per_push":       penetration_per_push,
    "drift_tip_class1":           drift_tip_class1,
    "drift_sleeve_class1":        drift_sleeve_class1,
    "drift_pore_class1":          drift_pore_class1,
    "drift_drill_string_class1":  drift_drill_string_class1,
    "class_downgrade":            class_downgrade,
}
