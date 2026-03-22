"""
QC Unified Scoring Engine
=========================
Linear interpolation scoring system, adapted from SeismicQC Suite's
scoring.py. Provides a generic, configurable scoring framework that
all QC domains can use.

Scoring approach:
1. Each QC metric maps to a component score via linear interpolation
2. Component scores are weighted and summed to produce a total (0-100)
3. Total score maps to a letter grade (A-F) via configurable boundaries

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import QCGrade, QCStatus


# ---------------------------------------------------------------------------
# Grade boundaries (configurable via YAML in future)
# ---------------------------------------------------------------------------

GRADE_BOUNDARIES: dict[QCGrade, float] = {
    QCGrade.A: 90.0,
    QCGrade.B: 80.0,
    QCGrade.C: 70.0,
    QCGrade.D: 60.0,
    QCGrade.F: 0.0,
}


def assign_grade(score: float) -> QCGrade:
    """Map a 0-100 score to a letter grade."""
    for grade in (QCGrade.A, QCGrade.B, QCGrade.C, QCGrade.D):
        if score >= GRADE_BOUNDARIES[grade]:
            return grade
    return QCGrade.F


# ---------------------------------------------------------------------------
# Linear interpolation scoring
# ---------------------------------------------------------------------------

@dataclass
class ScoreComponent:
    """Definition of a single scoring component.

    Attributes:
        name: Component identifier (e.g., "noise", "navigation", "snr")
        weight: Maximum points this component contributes (e.g., 10, 15, 20)
        best: Measured value that earns full score
        worst: Measured value that earns zero score
        higher_is_better: If True, larger values = better score
            (e.g., SNR dB, compliance %).
            If False, smaller values = better score
            (e.g., noise nT, spike %, dead trace %).
    """
    name: str
    weight: float
    best: float
    worst: float
    higher_is_better: bool = True

    def score(self, value: float) -> float:
        """Compute score for a measured value.

        Returns:
            Score from 0 to self.weight (linear interpolation).
        """
        if self.best == self.worst:
            return self.weight  # avoid div by zero

        if self.higher_is_better:
            # Higher value = better → normalize (value - worst) / (best - worst)
            normalized = (value - self.worst) / (self.best - self.worst)
        else:
            # Lower value = better → normalize (worst - value) / (worst - best)
            normalized = (self.worst - value) / (self.worst - self.best)

        normalized = max(0.0, min(1.0, normalized))
        return normalized * self.weight


@dataclass
class ScoringProfile:
    """A complete scoring profile for a QC domain.

    Defines all components, their weights, and thresholds.
    Weights should sum to 100 for intuitive total scores.
    """
    name: str
    components: list[ScoreComponent] = field(default_factory=list)

    @property
    def max_score(self) -> float:
        return sum(c.weight for c in self.components)

    def validate(self) -> list[str]:
        """Check profile for issues."""
        issues = []
        total_weight = self.max_score
        if abs(total_weight - 100.0) > 0.01:
            issues.append(
                f"Weights sum to {total_weight:.1f}, expected 100.0"
            )
        names = [c.name for c in self.components]
        if len(names) != len(set(names)):
            issues.append("Duplicate component names detected")
        return issues


def compute_score(
    profile: ScoringProfile,
    measurements: dict[str, float],
    missing_penalty: float = 0.6,
) -> dict:
    """Compute total QC score from measurements.

    Args:
        profile: Scoring profile defining components and thresholds.
        measurements: Dict mapping component names to measured values.
        missing_penalty: Score fraction for missing measurements (0-1).
            Default 0.6 = 60% of max weight for components without data.

    Returns:
        Dict with:
            total_score: 0-100 float
            grade: QCGrade
            status: QCStatus
            components: list of per-component dicts
    """
    components = []
    total = 0.0

    for comp in profile.components:
        if comp.name in measurements:
            value = measurements[comp.name]
            score = comp.score(value)
            components.append({
                "name": comp.name,
                "value": value,
                "score": round(score, 2),
                "max": comp.weight,
                "pct": round((score / comp.weight * 100) if comp.weight > 0 else 0, 1),
            })
            total += score
        else:
            # Missing data: assign neutral score
            fallback = comp.weight * missing_penalty
            components.append({
                "name": comp.name,
                "value": None,
                "score": round(fallback, 2),
                "max": comp.weight,
                "pct": round(missing_penalty * 100, 1),
                "missing": True,
            })
            total += fallback

    # Normalize to 0-100 if max_score != 100
    if profile.max_score > 0 and abs(profile.max_score - 100.0) > 0.01:
        total = (total / profile.max_score) * 100.0

    total = round(max(0.0, min(100.0, total)), 1)
    grade = assign_grade(total)
    status = QCStatus.from_score(total)

    return {
        "total_score": total,
        "grade": grade,
        "status": status,
        "components": components,
        "profile_name": profile.name,
    }


# ---------------------------------------------------------------------------
# Pre-built scoring profiles for each domain
# ---------------------------------------------------------------------------

MAG_SCORING_PROFILE = ScoringProfile(
    name="MAG QC",
    components=[
        ScoreComponent("noise_pp", 25, best=0.5, worst=5.0, higher_is_better=False),
        ScoreComponent("fourth_diff_exceedance", 25, best=0.0, worst=10.0, higher_is_better=False),
        ScoreComponent("spike_pct", 20, best=0.0, worst=5.0, higher_is_better=False),
        ScoreComponent("integrity_pct", 15, best=100.0, worst=80.0, higher_is_better=True),
        ScoreComponent("timestamp_regularity", 15, best=100.0, worst=80.0, higher_is_better=True),
    ],
)

SONAR_SCORING_PROFILE = ScoringProfile(
    name="Sonar QC",
    components=[
        ScoreComponent("altitude_compliance", 20, best=100.0, worst=70.0, higher_is_better=True),
        ScoreComponent("coverage_pct", 20, best=200.0, worst=80.0, higher_is_better=True),
        ScoreComponent("trackline_straightness", 15, best=100.0, worst=50.0, higher_is_better=True),
        ScoreComponent("noise_score", 15, best=100.0, worst=40.0, higher_is_better=True),
        ScoreComponent("location_fix_rate", 15, best=100.0, worst=85.0, higher_is_better=True),
        ScoreComponent("snr_db", 15, best=25.0, worst=5.0, higher_is_better=True),
    ],
)

SEISMIC_SCORING_PROFILE = ScoringProfile(
    name="Seismic QC",
    components=[
        ScoreComponent("navigation_coverage", 20, best=100.0, worst=80.0, higher_is_better=True),
        ScoreComponent("snr_db", 15, best=25.0, worst=5.0, higher_is_better=True),
        ScoreComponent("seafloor_consistency", 10, best=2.0, worst=20.0, higher_is_better=False),
        ScoreComponent("penetration_ms", 10, best=40.0, worst=10.0, higher_is_better=True),
        ScoreComponent("spectrum_bandwidth", 10, best=5000.0, worst=500.0, higher_is_better=True),
        ScoreComponent("integrity_dead_pct", 10, best=0.0, worst=5.0, higher_is_better=False),
        ScoreComponent("data_quality", 10, best=0.0, worst=3.0, higher_is_better=False),
        ScoreComponent("system_detect", 5, best=1.0, worst=0.0, higher_is_better=True),
        ScoreComponent("anomaly_rate", 5, best=0.0, worst=20.0, higher_is_better=False),
        ScoreComponent("consistency_cv", 5, best=10.0, worst=50.0, higher_is_better=False),
    ],
)

MBES_SCORING_PROFILE = ScoringProfile(
    name="MBES QC",
    components=[
        # Coverage: percentage of planned survey area with valid soundings
        ScoreComponent("coverage_pct", 25, best=100.0, worst=80.0, higher_is_better=True),
        # Crossline: crossline agreement std-dev in meters (lower = better)
        ScoreComponent("crossline_std_m", 20, best=0.1, worst=1.0, higher_is_better=False),
        # SVP: sound velocity profile residual in m/s (lower = better)
        ScoreComponent("svp_residual_ms", 20, best=0.0, worst=5.0, higher_is_better=False),
        # Motion: motion sensor residual in degrees (lower = better)
        ScoreComponent("motion_residual_deg", 20, best=0.0, worst=2.0, higher_is_better=False),
        # Vessel config: static offset verification score (higher = better)
        ScoreComponent("vessel_config_score", 15, best=100.0, worst=50.0, higher_is_better=True),
    ],
)
