"""
Sonar (SSS) QC Scoring Profile
================================
Domain-specific scoring profile for Side-Scan Sonar quality control.
Re-exports and extends the unified scoring engine from ``common.scoring``.

Components:
    - coverage (20):       Swath coverage as % of planned area
    - altitude (20):       Altitude compliance within range % bounds
    - noise (15):          Noise quality score (SNR, edge, stripe)
    - trackline (15):      Trackline straightness / deviation
    - location (15):       GNSS fix rate and position accuracy
    - snr_db (15):         Signal-to-noise ratio in dB

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

from ..common.scoring import (
    ScoreComponent,
    ScoringProfile,
    compute_score,
    assign_grade,
    SONAR_SCORING_PROFILE,
)

# Re-export the canonical profile defined in common.scoring
__all__ = [
    "SONAR_SCORING_PROFILE",
    "ScoreComponent",
    "ScoringProfile",
    "compute_score",
    "assign_grade",
    "compute_sonar_score",
]


def compute_sonar_score(
    measurements: dict[str, float],
    missing_penalty: float = 0.6,
) -> dict:
    """Convenience wrapper: compute sonar QC score.

    Args:
        measurements: Dict mapping component names to measured values.
            Expected keys (any subset accepted):
                ``coverage_pct``, ``altitude_compliance``,
                ``trackline_straightness``, ``noise_score``,
                ``location_fix_rate``, ``snr_db``.
        missing_penalty: Fraction of max weight for missing components.

    Returns:
        Dict with ``total_score``, ``grade``, ``status``, ``components``,
        ``profile_name``.
    """
    return compute_score(SONAR_SCORING_PROFILE, measurements, missing_penalty)
