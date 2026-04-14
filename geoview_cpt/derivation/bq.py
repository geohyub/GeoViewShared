"""
geoview_cpt.derivation.bq
================================
Eq 4 — normalized pore-pressure parameter ``Bq``.

    Bq = (u₂ − u₀) / (qt − σ_v0)

Numerator and denominator are evaluated in kPa. Where ``(qt − σ_v0)``
is below a small floor (i.e. the first few centimetres of penetration
where qt ≈ 0) the result is set to 0 instead of ±∞ so downstream charts
and Ic computations stay finite.
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.correction.units import to_kpa
from geoview_cpt.model import CPTChannel

__all__ = ["compute_bq"]


_QNET_FLOOR_KPA = 1.0   # 1 kPa floor for qt - σv0


def compute_bq(
    u2: CPTChannel,
    u0: CPTChannel,
    qt: CPTChannel,
    sigma_v0: CPTChannel,
) -> CPTChannel:
    """
    Compute Bq channel.

    Args:
        u2:        measured pore pressure (MPa or kPa).
        u0:        hydrostatic pore pressure (kPa — produced by
                   :func:`geoview_cpt.correction.u0.hydrostatic_pressure`).
        qt:        corrected cone resistance (MPa or kPa).
        sigma_v0:  total vertical stress (kPa).

    Returns:
        :class:`CPTChannel` named ``"Bq"`` with unit ``"-"``.
    """
    u2_kpa = to_kpa(u2)
    u0_kpa = to_kpa(u0)
    qt_kpa = to_kpa(qt)
    sv0_kpa = to_kpa(sigma_v0)
    if not (u2_kpa.shape == u0_kpa.shape == qt_kpa.shape == sv0_kpa.shape):
        raise ValueError(
            "Bq inputs must share shape: "
            f"u2={u2_kpa.shape} u0={u0_kpa.shape} "
            f"qt={qt_kpa.shape} sigma_v0={sv0_kpa.shape}"
        )

    qnet = qt_kpa - sv0_kpa
    bq = np.zeros_like(qnet)
    valid = qnet > _QNET_FLOOR_KPA
    bq[valid] = (u2_kpa[valid] - u0_kpa[valid]) / qnet[valid]
    return CPTChannel(name="Bq", unit="-", values=bq)
