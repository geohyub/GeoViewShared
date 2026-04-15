"""
geoview_cpt.liquefaction.boulanger_idriss_2014
================================================
Boulanger & Idriss (2014) CPT-based liquefaction triggering.

Reference: Boulanger R.W. & Idriss I.M. (2014) "CPT and SPT based
liquefaction triggering procedures", UC Davis CGM Report No. UCD/CGM-14/01.

Key differences from Robertson & Wride 1998:

 - Different CRR equation (exponential form, tuned to Chinese Seismic
   Database). Includes ``C_FC`` fines-content correction.
 - MSF uses Boulanger & Idriss 2014 formula (more conservative at high
   magnitudes than Youd 2001).
 - Adds ``K_σ`` overburden correction on the CSR side.
 - Adds ``rd`` from Idriss 1999 (depth-dependent, with explicit
   magnitude dependence). We ship the simpler Cetin et al. 2004 form
   as a second option.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from geoview_cpt.liquefaction.common import (
    EarthquakeScenario,
    LabelLiterals,
    LiquefactionProfile,
)
from geoview_cpt.liquefaction.robertson_wride_1998 import CLAY_LIKE_IC_THRESHOLD

__all__ = [
    "boulanger_idriss_2014_crr",
    "msf_boulanger_idriss_2014",
    "k_sigma_boulanger_idriss_2014",
    "rd_idriss_1999",
    "triggering_boulanger_idriss_2014",
]


def boulanger_idriss_2014_crr(
    qtn: np.ndarray,
    ic: np.ndarray,
    *,
    apply_fines_correction: bool = True,
) -> np.ndarray:
    """
    B&I 2014 Eq 2.12 — CRR_7.5_1atm for clean sand, then fines correction.

        CRR = exp((Q/113) + (Q/1000)² − (Q/140)³ + (Q/137)⁴ − 2.80)

    with ``Q = qtn,cs`` (fines-corrected Qtn). The fines correction is
    a simplified ``ΔQtn = (5.4 + Q/16) × exp(1.63 + 9.7/(FC+0.01) −
    (15.7/(FC+0.01))²)`` using ``FC`` estimated from Ic via B&I 2014
    Eq 2.8 (``FC = 80 × (Ic + 0.29) − 137``, clamped to 0..100).
    """
    qtn = np.asarray(qtn, dtype=np.float64)
    ic = np.asarray(ic, dtype=np.float64)

    if apply_fines_correction:
        fc = 80.0 * (ic + 0.29) - 137.0
        fc = np.clip(fc, 0.0, 100.0)
        delta_q = (5.4 + qtn / 16.0) * np.exp(
            1.63
            + 9.7 / (fc + 0.01)
            - (15.7 / (fc + 0.01)) ** 2
        )
        qtn_cs = qtn + delta_q
    else:
        qtn_cs = qtn

    exponent = (
        (qtn_cs / 113.0)
        + (qtn_cs / 1000.0) ** 2
        - (qtn_cs / 140.0) ** 3
        + (qtn_cs / 137.0) ** 4
        - 2.80
    )
    crr = np.exp(exponent)
    return np.clip(crr, 0.0, 2.0)


def msf_boulanger_idriss_2014(mw: float) -> float:
    """
    B&I 2014 Eq 2.4 — magnitude scaling factor:

        MSF = 1 + (MSF_max − 1) × (8.64 × exp(−Mw/4) − 1.325)

    with ``MSF_max = 1.8`` (clean sand upper bound).
    """
    if mw <= 0:
        raise ValueError(f"mw must be positive, got {mw}")
    msf_max = 1.8
    return 1.0 + (msf_max - 1.0) * (8.64 * np.exp(-mw / 4.0) - 1.325)


def k_sigma_boulanger_idriss_2014(
    sigma_prime_v0_kpa: np.ndarray,
    qtn_cs: np.ndarray | None = None,
) -> np.ndarray:
    """
    B&I 2014 Eq 2.16 — overburden correction K_σ on CSR.

        K_σ = 1 − C_σ × ln(σ'v0 / pa)
        C_σ = 1 / (37.3 − 8.27 × (Qtn,cs)^0.264)

    ``qtn_cs`` is needed for ``C_σ`` — pass the same array used inside
    :func:`boulanger_idriss_2014_crr` or fall back to a flat ``C_σ = 0.1``
    when omitted.
    """
    spv0 = np.asarray(sigma_prime_v0_kpa, dtype=np.float64)
    pa = 100.0
    if qtn_cs is None:
        c_sigma = np.full_like(spv0, 0.1)
    else:
        q = np.clip(np.asarray(qtn_cs, dtype=np.float64), 21.0, 211.0)
        c_sigma = 1.0 / (37.3 - 8.27 * q ** 0.264)
    k_sigma = 1.0 - c_sigma * np.log(np.clip(spv0 / pa, 1e-3, None))
    return np.clip(k_sigma, 0.5, 1.2)


def rd_idriss_1999(depth_m: np.ndarray, mw: float) -> np.ndarray:
    """
    Idriss 1999 (NCEER workshop consensus) depth-dependent stress
    reduction with explicit magnitude dependence.

        α(z) = −1.012 − 1.126·sin(z/11.73 + 5.133)
        β(z) =  0.106 + 0.118·sin(z/11.28 + 5.142)
        ln(rd) = α + β·Mw
    """
    z = np.clip(np.asarray(depth_m, dtype=np.float64), 0.0, 34.0)
    alpha = -1.012 - 1.126 * np.sin(z / 11.73 + 5.133)
    beta = 0.106 + 0.118 * np.sin(z / 11.28 + 5.142)
    rd = np.exp(alpha + beta * mw)
    return np.clip(rd, 0.1, 1.2)


def _label_fs(fs: float, ic: float) -> LabelLiterals:
    if ic > CLAY_LIKE_IC_THRESHOLD:
        return "clay_like"
    if not np.isfinite(fs):
        return "n/a"
    if fs < 1.0:
        return "liquefiable"
    if fs < 1.2:
        return "marginal"
    return "non_liquefiable"


def triggering_boulanger_idriss_2014(
    *,
    scenario: EarthquakeScenario,
    depth_m: Sequence[float],
    qtn: Sequence[float],
    ic: Sequence[float],
    sigma_v0_kpa: Sequence[float],
    sigma_prime_v0_kpa: Sequence[float],
) -> LiquefactionProfile:
    """Run the B&I 2014 triggering pipeline end-to-end."""
    depth = np.asarray(depth_m, dtype=np.float64)
    qtn_arr = np.asarray(qtn, dtype=np.float64)
    ic_arr = np.asarray(ic, dtype=np.float64)
    sv0 = np.asarray(sigma_v0_kpa, dtype=np.float64)
    spv0 = np.asarray(sigma_prime_v0_kpa, dtype=np.float64)

    if not (depth.shape == qtn_arr.shape == ic_arr.shape == sv0.shape == spv0.shape):
        raise ValueError("all input arrays must share shape")

    # Clean-sand equivalent Qtn for both CRR and K_σ
    fc = np.clip(80.0 * (ic_arr + 0.29) - 137.0, 0.0, 100.0)
    delta_q = (5.4 + qtn_arr / 16.0) * np.exp(
        1.63 + 9.7 / (fc + 0.01) - (15.7 / (fc + 0.01)) ** 2
    )
    qtn_cs = np.where(
        scenario.fines_correction, qtn_arr + delta_q, qtn_arr,
    )

    crr = boulanger_idriss_2014_crr(qtn_arr, ic_arr, apply_fines_correction=scenario.fines_correction)
    msf = msf_boulanger_idriss_2014(scenario.magnitude_mw)
    k_sigma = k_sigma_boulanger_idriss_2014(spv0, qtn_cs=qtn_cs)
    rd = rd_idriss_1999(depth, scenario.magnitude_mw)

    spv0_safe = np.clip(spv0, 1e-3, None)
    csr = 0.65 * scenario.pga_g * (sv0 / spv0_safe) * rd
    # Apply Kσ correction on the CRR side (B&I convention)
    crr_corrected = crr * k_sigma

    with np.errstate(divide="ignore", invalid="ignore"):
        fs = np.where(csr > 1e-9, crr_corrected * msf / csr, np.nan)

    fs_final = np.where(ic_arr > CLAY_LIKE_IC_THRESHOLD, np.nan, fs)
    labels: list[LabelLiterals] = [
        _label_fs(float(f), float(i)) for f, i in zip(fs_final, ic_arr)
    ]

    return LiquefactionProfile(
        method="boulanger_idriss_2014",
        scenario=scenario,
        depth_m=depth,
        crr=crr_corrected,
        csr=csr,
        fs=fs_final,
        labels=labels,
        extras={
            "Qtn_cs": qtn_cs,
            "fines_content_pct": fc,
            "msf": msf,
            "k_sigma": k_sigma,
            "rd": rd,
        },
    )
