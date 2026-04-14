"""
geoview_cpt.derivation.ic
================================
Robertson normalized resistance / friction ratio / Soil Behavior Index.

References:
    Robertson, P.K. (1990) — Soil classification using the cone penetration test.
    Robertson, P.K. & Wride, C.E. (1998) — Evaluating cyclic liquefaction
        potential using the cone penetration test.

    Qt1 = (qt − σ_v0) / σ'_v0          (dimensionless)
    Fr  = fs / (qt − σ_v0) × 100       (%)
    Ic  = √[(3.47 − log₁₀(Qt1))² + (log₁₀(Fr) + 1.22)²]

Inputs go through :func:`geoview_cpt.correction.units.to_kpa` so the
"fs in kPa, qc in MPa" parser convention is handled inside the formula.
A small floor protects log10 from crashing on the first noise samples.
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.correction.units import to_kpa
from geoview_cpt.model import CPTChannel

__all__ = [
    "compute_qt_normalized",
    "compute_fr_normalized",
    "compute_ic",
]


_QNET_FLOOR_KPA = 1.0
_LOG_FLOOR = 1e-3


def compute_qt_normalized(
    qt: CPTChannel,
    sigma_v0: CPTChannel,
    sigma_prime_v0: CPTChannel,
) -> CPTChannel:
    """Robertson 1990 normalized resistance ``Qt1``."""
    qt_kpa = to_kpa(qt)
    sv0 = to_kpa(sigma_v0)
    spv0 = to_kpa(sigma_prime_v0)
    if not (qt_kpa.shape == sv0.shape == spv0.shape):
        raise ValueError(
            "Qt1 inputs must share shape: "
            f"qt={qt_kpa.shape} sv0={sv0.shape} spv0={spv0.shape}"
        )
    qnet = qt_kpa - sv0
    safe_spv0 = np.where(spv0 > _LOG_FLOOR, spv0, _LOG_FLOOR)
    qt1 = np.where(spv0 > _LOG_FLOOR, qnet / safe_spv0, 0.0)
    return CPTChannel(name="Qt1", unit="-", values=qt1)


def compute_fr_normalized(
    fs: CPTChannel,
    qt: CPTChannel,
    sigma_v0: CPTChannel,
) -> CPTChannel:
    """Robertson 1990 normalized friction ratio ``Fr (%)``."""
    fs_kpa = to_kpa(fs)
    qt_kpa = to_kpa(qt)
    sv0 = to_kpa(sigma_v0)
    if not (fs_kpa.shape == qt_kpa.shape == sv0.shape):
        raise ValueError(
            "Fr inputs must share shape: "
            f"fs={fs_kpa.shape} qt={qt_kpa.shape} sv0={sv0.shape}"
        )
    qnet = qt_kpa - sv0
    fr = np.zeros_like(qnet)
    valid = qnet > _QNET_FLOOR_KPA
    fr[valid] = (fs_kpa[valid] / qnet[valid]) * 100.0
    return CPTChannel(name="Fr", unit="%", values=fr)


def compute_ic(qt_normalized: CPTChannel, fr: CPTChannel) -> CPTChannel:
    """
    Robertson & Wride 1998 Soil Behavior Type Index.

        Ic = √[(3.47 − log₁₀(Qt))² + (log₁₀(Fr) + 1.22)²]

    The first argument is the **normalized resistance** — pass ``Qt1``
    for the Robertson 1990 linear normalization or ``Qtn`` for the
    Robertson 2009 iterative variant. CPeT-IT and most modern reports
    use the iterative ``Qtn`` (the iterative deriver is open-question
    Q35 — for now feed CPeT-IT's ``Qtn`` column directly when validating
    against commercial output).

    Both arguments are dimensionless / percent and are clipped to a
    floor before ``log10`` so the result stays finite at very low qt.
    """
    if qt_normalized.values.shape != fr.values.shape:
        raise ValueError(
            "Ic inputs must share shape: "
            f"qt={qt_normalized.values.shape} fr={fr.values.shape}"
        )
    qt_clip = np.clip(qt_normalized.values, _LOG_FLOOR, None)
    fr_clip = np.clip(fr.values, _LOG_FLOOR, None)
    a = 3.47 - np.log10(qt_clip)
    b = np.log10(fr_clip) + 1.22
    ic = np.sqrt(a * a + b * b)
    return CPTChannel(name="Ic", unit="-", values=ic)
