"""
geoview_cpt.derivation.gamma
================================
Robertson & Cabal (2010) bulk unit-weight estimator.

    γ / γ_w = 0.27 × log₁₀(Rf) + 0.36 × log₁₀(qt / pa) + 1.236

with ``pa = 100 kPa`` (atmospheric reference) and ``γ_w`` = 9.81 kN/m³
default. This is the "AutoGamma" CPeT-IT users see in the Various
block, and it's the source of truth for σ_v0 integration when the user
hasn't supplied layer-by-layer overrides.
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.correction.u0 import DEFAULT_GAMMA_W_KN_M3
from geoview_cpt.correction.units import to_kpa
from geoview_cpt.model import CPTChannel

__all__ = ["estimate_gamma_robertson_cabal_2010"]


_PA_KPA = 100.0
_RF_FLOOR_PCT = 0.1
_QT_FLOOR_RATIO = 0.01   # qt / pa lower clip


def estimate_gamma_robertson_cabal_2010(
    qt: CPTChannel,
    rf: CPTChannel,
    *,
    gamma_w: float = DEFAULT_GAMMA_W_KN_M3,
) -> CPTChannel:
    """
    Compute the γ profile (kN/m³) from corrected cone resistance and
    friction ratio.

    Args:
        qt:      corrected cone resistance (MPa or kPa).
        rf:      friction ratio (%) from
                 :func:`geoview_cpt.derivation.rf.compute_rf`.
        gamma_w: water unit weight (kN/m³).

    Returns:
        :class:`CPTChannel` named ``"gamma"`` with unit ``"kN/m^3"``.
    """
    if gamma_w <= 0:
        raise ValueError(f"gamma_w must be positive, got {gamma_w}")
    qt_kpa = to_kpa(qt)
    rf_pct = rf.values
    if qt_kpa.shape != rf_pct.shape:
        raise ValueError(
            f"qt/Rf shape mismatch: {qt_kpa.shape} vs {rf_pct.shape}"
        )

    rf_safe = np.clip(rf_pct, _RF_FLOOR_PCT, None)
    qt_ratio = np.clip(qt_kpa / _PA_KPA, _QT_FLOOR_RATIO, None)
    g_ratio = 0.27 * np.log10(rf_safe) + 0.36 * np.log10(qt_ratio) + 1.236
    gamma = g_ratio * gamma_w
    return CPTChannel(name="gamma", unit="kN/m^3", values=gamma)
