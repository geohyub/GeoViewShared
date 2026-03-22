"""
MBES (Multibeam Echo Sounder) QC Scoring Profile
==================================================
Domain-specific scoring profile for Multibeam quality control.
Re-exports and extends the unified scoring engine from ``common.scoring``.

Components:
    - coverage (25):         Survey coverage % of planned area
    - crossline (20):        Crossline agreement std-dev in meters (lower = better)
    - svp (20):              Sound velocity profile residual in m/s (lower = better)
    - motion (20):           Motion sensor residual in degrees (lower = better)
    - vessel_config (15):    Static offset verification score (higher = better)

Weights sum to 100.

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

from ..common.scoring import (
    ScoreComponent,
    ScoringProfile,
    compute_score,
    assign_grade,
    MBES_SCORING_PROFILE,
)

# Re-export the canonical profile defined in common.scoring
__all__ = [
    "MBES_SCORING_PROFILE",
    "ScoreComponent",
    "ScoringProfile",
    "compute_score",
    "assign_grade",
    "compute_mbes_score",
]


def compute_mbes_score(
    measurements: dict[str, float],
    missing_penalty: float = 0.6,
) -> dict:
    """Convenience wrapper: compute MBES QC score.

    Args:
        measurements: Dict mapping component names to measured values.
            Expected keys (any subset accepted):
                ``coverage_pct``, ``crossline_std_m``,
                ``svp_residual_ms``, ``motion_residual_deg``,
                ``vessel_config_score``.
        missing_penalty: Fraction of max weight for missing components.

    Returns:
        Dict with ``total_score``, ``grade``, ``status``, ``components``,
        ``profile_name``.
    """
    return compute_score(MBES_SCORING_PROFILE, measurements, missing_penalty)
