"""
geoview_cpt.settlement.schmertmann
================================
Schmertmann 1970 / Schmertmann et al. 1978 influence-factor method.

Reference: Schmertmann J.H. (1970) "Static cone to compute static
settlement over sand", JSMFD, ASCE, 96(SM3); Schmertmann et al. (1978)
"Improved strain influence factor diagrams".

    S = C₁ · C₂ · Δp · ∑ (Iz / E) · Δz

Influence factor diagram (1978 update, square/round footing):

    Iz(0)       = 0.1
    Iz(B/2)     = 0.5  (peak)
    Iz(2·B)     = 0
    linear between vertices.

For strip footings (L/B ≥ 10) the peak shifts to ``B`` and the end
depth to ``4·B`` — pass ``strip=True`` to enable that variant.

``C₁`` is the embedment correction (``1 − 0.5 · σ'v0,foundation /
Δp``) and ``C₂`` is the creep factor (``1 + 0.2 · log10(t_yr / 0.1)``,
set ``t_yr=0.1`` for immediate).
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.settlement.common import FoundationLoad, SettlementResult

__all__ = ["schmertmann_settlement"]


def _influence_factor(
    depth_below_base_m: np.ndarray,
    width_m: float,
    *,
    strip: bool = False,
) -> np.ndarray:
    """Schmertmann 1978 Iz diagram."""
    z = np.asarray(depth_below_base_m, dtype=np.float64)
    if strip:
        z_peak = width_m
        z_end = 4.0 * width_m
    else:
        z_peak = 0.5 * width_m
        z_end = 2.0 * width_m
    iz_peak = 0.5
    iz0 = 0.1

    iz = np.where(
        z < 0,
        0.0,
        np.where(
            z <= z_peak,
            iz0 + (iz_peak - iz0) * (z / z_peak) if z_peak > 0 else iz0,
            np.where(
                z <= z_end,
                iz_peak * (1 - (z - z_peak) / (z_end - z_peak)),
                0.0,
            ),
        ),
    )
    return np.clip(iz, 0.0, 0.6)


def _c1_embedment(
    sigma_prime_v0_foundation_kpa: float,
    net_bearing_kpa: float,
) -> float:
    ratio = sigma_prime_v0_foundation_kpa / max(net_bearing_kpa, 1e-3)
    return max(1.0 - 0.5 * ratio, 0.5)


def _c2_creep(t_yr: float) -> float:
    t_safe = max(t_yr, 0.1)
    return 1.0 + 0.2 * np.log10(t_safe / 0.1)


def schmertmann_settlement(
    load: FoundationLoad,
    depth_m: np.ndarray,
    elastic_modulus_kpa: np.ndarray,
    *,
    sigma_prime_v0_at_foundation_kpa: float = 0.0,
    strip: bool = False,
    time_years: float = 0.1,
) -> SettlementResult:
    """
    Schmertmann 1978 settlement integration.

    Args:
        load:                              :class:`FoundationLoad`.
        depth_m:                           depth array from ground surface.
        elastic_modulus_kpa:               drained E per sample (kPa).
        sigma_prime_v0_at_foundation_kpa:  effective overburden at the
                                           founding depth (kPa).
        strip:                             True for strip footing (L/B ≥ 10).
        time_years:                        time since construction for the
                                           creep correction. 0.1 yr = immediate.

    Returns:
        :class:`SettlementResult` with per-layer contributions (mm).
    """
    z = np.asarray(depth_m, dtype=np.float64)
    e_kpa = np.asarray(elastic_modulus_kpa, dtype=np.float64)
    if z.shape != e_kpa.shape:
        raise ValueError(f"depth / E shape mismatch: {z.shape} vs {e_kpa.shape}")
    if z.size < 2:
        return SettlementResult(
            total_mm=0.0, per_layer_mm=np.zeros(0), depth_m=z,
            method="schmertmann",
        )

    z_below = np.clip(z - load.depth_m, 0.0, None)
    iz = _influence_factor(z_below, load.width_m, strip=strip)
    dz = np.diff(z_below, append=z_below[-1])
    dz = np.clip(dz, 0.0, None)

    c1 = _c1_embedment(sigma_prime_v0_at_foundation_kpa, load.net_bearing_kpa)
    c2 = _c2_creep(time_years)

    e_safe = np.clip(e_kpa, 1e-3, None)
    integrand = iz / e_safe * dz
    layer_strain_m = c1 * c2 * load.net_bearing_kpa * integrand
    per_layer_mm = layer_strain_m * 1000.0

    return SettlementResult(
        total_mm=float(np.sum(per_layer_mm)),
        per_layer_mm=per_layer_mm,
        depth_m=z,
        method="schmertmann",
        extras={
            "Iz": iz,
            "C1": c1,
            "C2": c2,
            "elastic_modulus_kpa": e_kpa,
            "strip": strip,
            "time_years": time_years,
        },
    )
