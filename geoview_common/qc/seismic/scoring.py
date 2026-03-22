"""
Seismic QC Scoring Profile
============================
Domain-specific scoring profile for Sub-Bottom Profiler / Seismic quality control.
Re-exports and extends the unified scoring engine from ``common.scoring``.

Components:
    - navigation (20):       Navigation / GNSS coverage %
    - signal_quality (15):   SNR in dB
    - penetration (10):      Penetration depth in ms (TWT)
    - spectrum (10):         Usable spectrum bandwidth in Hz
    - integrity (10):        Dead/bad trace percentage (lower = better)
    - seafloor (10):         Seafloor pick consistency std-dev (lower = better)
    - data_quality (10):     Overall data quality score (lower = better)
    - system_detect (5):     System auto-detection confidence
    - anomaly_rate (5):      Anomaly detection rate % (lower = better)
    - consistency_cv (5):    Amplitude consistency CV % (lower = better)

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

from ..common.scoring import (
    ScoreComponent,
    ScoringProfile,
    compute_score,
    assign_grade,
    SEISMIC_SCORING_PROFILE,
)

# Re-export the canonical profile defined in common.scoring
__all__ = [
    "SEISMIC_SCORING_PROFILE",
    "ScoreComponent",
    "ScoringProfile",
    "compute_score",
    "assign_grade",
    "compute_seismic_score",
]


def compute_seismic_score(
    measurements: dict[str, float],
    missing_penalty: float = 0.6,
) -> dict:
    """Convenience wrapper: compute seismic QC score.

    Args:
        measurements: Dict mapping component names to measured values.
            Expected keys (any subset accepted):
                ``navigation_coverage``, ``snr_db``,
                ``seafloor_consistency``, ``penetration_ms``,
                ``spectrum_bandwidth``, ``integrity_dead_pct``,
                ``data_quality``, ``system_detect``,
                ``anomaly_rate``, ``consistency_cv``.
        missing_penalty: Fraction of max weight for missing components.

    Returns:
        Dict with ``total_score``, ``grade``, ``status``, ``components``,
        ``profile_name``.
    """
    return compute_score(SEISMIC_SCORING_PROFILE, measurements, missing_penalty)
