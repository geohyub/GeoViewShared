"""
geoview_cpt.settlement.mayne_1d
================================
Mayne 1-D elastic compression.

Reference: Mayne P.W. (2007) "In-situ test calibrations for evaluating
soil parameters", Characterisation and Engineering Properties of
Natural Soils, Taylor & Francis.

Layer compression:

    ΔH_i = Δσ_i · h_i / E_i

where ``h_i`` is the sublayer thickness and ``E_i`` is the drained
Young's modulus. In the simplified 1-D version (Boussinesq-adjusted
pressure bulb not applied) the stress increment ``Δσ`` is the net
bearing pressure ``q_net`` attenuated by a trapezoidal influence
factor so the deepest layers contribute less.
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.settlement.common import FoundationLoad, SettlementResult

__all__ = ["mayne_1d_settlement"]


def _depth_influence(depth_below_base: np.ndarray, width_m: float) -> np.ndarray:
    """
    Simplified trapezoidal stress spread — 2:1 method.

        Δσ / q = (B · L) / ((B + z) · (L + z))

    For square footings (L = B) this collapses to 1/(1 + z/B)².
    """
    z = np.asarray(depth_below_base, dtype=np.float64)
    return 1.0 / (1.0 + z / width_m) ** 2


def mayne_1d_settlement(
    load: FoundationLoad,
    depth_m: np.ndarray,
    elastic_modulus_kpa: np.ndarray,
) -> SettlementResult:
    """
    Compute total + per-layer settlement via Mayne 1-D.

    Args:
        load:                 :class:`FoundationLoad`.
        depth_m:              depth array (m) measured from ground surface.
                              Must be monotonically increasing.
        elastic_modulus_kpa:  drained Young's modulus per sample (kPa).
                              Same length as ``depth_m``.

    Returns:
        :class:`SettlementResult` with per-layer contributions (mm).
    """
    z = np.asarray(depth_m, dtype=np.float64)
    e_kpa = np.asarray(elastic_modulus_kpa, dtype=np.float64)
    if z.shape != e_kpa.shape:
        raise ValueError(f"depth / E shape mismatch: {z.shape} vs {e_kpa.shape}")
    if z.size < 2:
        return SettlementResult(
            total_mm=0.0, per_layer_mm=np.zeros(0),
            depth_m=z, method="mayne_1d",
        )

    # Shift so only depths below the foundation base contribute
    z_below = np.clip(z - load.depth_m, 0.0, None)

    # Trapezoidal sub-layer thicknesses — use forward differences
    dz = np.diff(z_below, append=z_below[-1])
    dz = np.clip(dz, 0.0, None)

    iz = _depth_influence(z_below, load.width_m)
    delta_sigma = load.net_bearing_kpa * iz    # kPa
    e_safe = np.clip(e_kpa, 1e-3, None)
    delta_h_m = delta_sigma * dz / e_safe
    delta_h_mm = delta_h_m * 1000.0

    total_mm = float(np.sum(delta_h_mm))
    return SettlementResult(
        total_mm=total_mm,
        per_layer_mm=delta_h_mm,
        depth_m=z,
        method="mayne_1d",
        extras={
            "influence_factor": iz,
            "delta_sigma_kpa": delta_sigma,
            "elastic_modulus_kpa": e_kpa,
        },
    )
