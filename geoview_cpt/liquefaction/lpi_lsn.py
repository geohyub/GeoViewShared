"""
geoview_cpt.liquefaction.lpi_lsn
================================
Liquefaction severity indices.

LPI — Iwasaki et al. 1982/1986
    LPI = ∫₀²⁰ F(z) · w(z) dz

    F(z) = 1 − FS   (for FS < 1), else 0
    w(z) = 10 − 0.5·z  (0 ≤ z ≤ 20 m)

    Severity bands:
        LPI = 0       none
        0 < LPI ≤ 5   low
        5 < LPI ≤ 15  moderate
        LPI > 15      high

LSN — Tonkin & Taylor 2013
    LSN = 1000 · ∫₀²⁰ (εv(z) / z) dz

    where εv is the post-liquefaction volumetric strain estimated from
    the Zhang et al. 2002 (or Ishihara-Yoshimine) tables. For v1 we
    accept an externally-computed εv array — the synthesis module or a
    dedicated table-based deriver will populate it. When ``epsilon_v``
    is omitted the function falls back to a rough Zhang 2002 estimate
    from the factor of safety.
"""
from __future__ import annotations

from typing import Literal

import numpy as np

__all__ = [
    "compute_lpi",
    "compute_lsn",
    "classify_lpi",
    "classify_lsn",
]


# ---------------------------------------------------------------------------
# LPI
# ---------------------------------------------------------------------------


def compute_lpi(
    depth_m: np.ndarray,
    factor_of_safety: np.ndarray,
    *,
    max_depth_m: float = 20.0,
) -> float:
    """
    Iwasaki LPI integrated from 0 to ``max_depth_m``.

    Samples beyond ``max_depth_m`` are discarded; NaN FS values (e.g.
    clay layers) contribute zero. Uses a trapezoidal rule so uneven
    depth sampling is handled correctly.
    """
    z = np.asarray(depth_m, dtype=np.float64)
    fs = np.asarray(factor_of_safety, dtype=np.float64)
    if z.shape != fs.shape:
        raise ValueError(f"depth/fs shape mismatch: {z.shape} vs {fs.shape}")

    mask = z <= max_depth_m
    z = z[mask]
    fs = fs[mask]
    if z.size == 0:
        return 0.0

    f_hazard = np.where(np.isfinite(fs) & (fs < 1.0), 1.0 - fs, 0.0)
    weight = np.clip(10.0 - 0.5 * z, 0.0, 10.0)
    integrand = f_hazard * weight

    lpi = float(np.trapezoid(integrand, z))
    return max(0.0, lpi)


def classify_lpi(lpi: float) -> Literal["none", "low", "moderate", "high"]:
    if lpi <= 0.0:
        return "none"
    if lpi <= 5.0:
        return "low"
    if lpi <= 15.0:
        return "moderate"
    return "high"


# ---------------------------------------------------------------------------
# LSN
# ---------------------------------------------------------------------------


def _epsilon_v_zhang_2002(fs: np.ndarray) -> np.ndarray:
    """
    Rough Zhang et al. 2002 post-liquefaction volumetric strain.

    Uses the clean-sand curve at medium relative density:

        εv (%) = 0                      (FS ≥ 2.0)
        εv (%) = 102 × (2 − FS)²        (0 < FS < 2.0, capped at 6%)

    The fit is intentionally conservative for v1; a table-based
    accurate variant is open for a follow-up once the Zhang lookup is
    digitised.
    """
    fs = np.asarray(fs, dtype=np.float64)
    eps = np.zeros_like(fs)
    band = np.isfinite(fs) & (fs < 2.0)
    eps[band] = np.clip(102.0 * (2.0 - fs[band]) ** 2 / 100.0, 0.0, 6.0)
    return eps


def compute_lsn(
    depth_m: np.ndarray,
    factor_of_safety: np.ndarray,
    *,
    epsilon_v_pct: np.ndarray | None = None,
    max_depth_m: float = 20.0,
) -> float:
    """
    Tonkin & Taylor LSN integrated 0..``max_depth_m``.

    ``epsilon_v_pct`` is an optional override array (in %). When omitted
    we fall back to :func:`_epsilon_v_zhang_2002`.

    The integrand divides by ``z``; samples at ``z = 0`` are shifted to
    0.01 m to avoid a singularity.
    """
    z = np.asarray(depth_m, dtype=np.float64)
    fs = np.asarray(factor_of_safety, dtype=np.float64)
    if z.shape != fs.shape:
        raise ValueError(f"depth/fs shape mismatch: {z.shape} vs {fs.shape}")

    eps_v = (
        _epsilon_v_zhang_2002(fs)
        if epsilon_v_pct is None
        else np.asarray(epsilon_v_pct, dtype=np.float64)
    )
    if eps_v.shape != z.shape:
        raise ValueError("epsilon_v_pct must share shape with depth_m")

    mask = z <= max_depth_m
    z_mask = np.clip(z[mask], 0.01, None)
    eps_mask = eps_v[mask]
    if z_mask.size == 0:
        return 0.0

    lsn = 10.0 * float(np.trapezoid(eps_mask / z_mask, z_mask))
    return max(0.0, lsn)


def classify_lsn(lsn: float) -> Literal["none", "low", "moderate", "high", "very_high"]:
    if lsn <= 10:
        return "none"
    if lsn <= 20:
        return "low"
    if lsn <= 30:
        return "moderate"
    if lsn <= 50:
        return "high"
    return "very_high"
