"""
geoview_cpt.liquefaction.robertson_wride_1998
==============================================
CPT-based liquefaction triggering — Robertson & Wride (1998).

Reference: Robertson P.K. & Wride C.E. (1998), "Evaluating cyclic
liquefaction potential using the cone penetration test", Canadian
Geotechnical Journal 35(3).

Pipeline:

    1. Compute the equivalent clean-sand Qtn,cs via:
          K_c  = 1 (if Ic ≤ 1.64) else
                 −0.403·Ic⁴ + 5.581·Ic³ − 21.63·Ic² + 33.75·Ic − 17.88
          Qtn,cs = K_c · Qtn
    2. Ic > 2.6 → **clay-like, non-liquefiable** (NCEER 1997 screening).
    3. Qtn,cs → CRR_7.5 via Robertson & Wride 1998 Eq 10a/10b:
          Qtn,cs < 50  → CRR_7.5 = 0.833 · (Qtn,cs / 1000) + 0.05
          50 ≤ Qtn,cs < 160 → CRR_7.5 = 93 · (Qtn,cs / 1000)³ + 0.08
    4. CSR from Seed & Idriss 1971 with the Liao & Whitman 1986 rd.
    5. FS = CRR_7.5 · MSF / CSR    (MSF supplied by caller; Youd 2001 is
       the standard NCEER workshop default).
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from geoview_cpt.liquefaction.common import (
    EarthquakeScenario,
    LabelLiterals,
    LiquefactionProfile,
)

__all__ = [
    "CLAY_LIKE_IC_THRESHOLD",
    "fines_correction_kc",
    "crr_75_robertson_wride_1998",
    "robertson_wride_1998_crr",
    "stress_reduction_liao_whitman_1986",
    "csr_seed_idriss_1971",
    "triggering_robertson_wride_1998",
]


CLAY_LIKE_IC_THRESHOLD: float = 2.6
"""Robertson & Wride 1998: Ic above this is clay-like → non-liquefiable."""


def fines_correction_kc(ic: np.ndarray) -> np.ndarray:
    """Robertson & Wride 1998 Eq 8 — fines content correction factor."""
    arr = np.asarray(ic, dtype=np.float64)
    kc = np.where(
        arr <= 1.64,
        1.0,
        -0.403 * arr**4 + 5.581 * arr**3 - 21.63 * arr**2 + 33.75 * arr - 17.88,
    )
    # Clamp to [1.0, 5.0] — Robertson's intent; deeply weathered profiles
    # sometimes give bogus > 10 values through the quartic.
    return np.clip(kc, 1.0, 5.0)


def crr_75_robertson_wride_1998(qtn_cs: np.ndarray) -> np.ndarray:
    """Robertson & Wride 1998 Eq 10a/10b — CRR at M7.5 from Qtn,cs."""
    arr = np.asarray(qtn_cs, dtype=np.float64)
    crr = np.where(
        arr < 50.0,
        0.833 * (arr / 1000.0) + 0.05,
        93.0 * (arr / 1000.0) ** 3 + 0.08,
    )
    # Cap at 2.0 — Robertson notes the cubic diverges for very dense sand.
    return np.clip(crr, 0.0, 2.0)


def robertson_wride_1998_crr(
    qtn: np.ndarray,
    ic: np.ndarray,
    *,
    apply_fines_correction: bool = True,
) -> np.ndarray:
    """Convenience: Qtn + Ic → CRR_7.5."""
    qtn_cs = np.asarray(qtn, dtype=np.float64)
    if apply_fines_correction:
        qtn_cs = fines_correction_kc(ic) * qtn_cs
    return crr_75_robertson_wride_1998(qtn_cs)


def stress_reduction_liao_whitman_1986(depth_m: np.ndarray) -> np.ndarray:
    """
    Liao & Whitman 1986 simplified rd profile (accepted by NCEER 1997):

        rd = 1.0 − 0.00765·z     (z ≤ 9.15 m)
        rd = 1.174 − 0.0267·z    (9.15 < z ≤ 23 m)
        rd = 0.744 − 0.008·z     (23 < z ≤ 30 m)
        rd = 0.5                 (z > 30 m)
    """
    z = np.asarray(depth_m, dtype=np.float64)
    rd = np.where(
        z <= 9.15,
        1.0 - 0.00765 * z,
        np.where(
            z <= 23.0,
            1.174 - 0.0267 * z,
            np.where(z <= 30.0, 0.744 - 0.008 * z, 0.5),
        ),
    )
    return np.clip(rd, 0.2, 1.0)


def csr_seed_idriss_1971(
    sigma_v0_kpa: np.ndarray,
    sigma_prime_v0_kpa: np.ndarray,
    depth_m: np.ndarray,
    pga_g: float,
) -> np.ndarray:
    """
    CSR = 0.65 · (amax/g) · (σv0/σ'v0) · rd
    """
    rd = stress_reduction_liao_whitman_1986(depth_m)
    sv0 = np.asarray(sigma_v0_kpa, dtype=np.float64)
    spv0 = np.clip(np.asarray(sigma_prime_v0_kpa, dtype=np.float64), 1e-3, None)
    return 0.65 * pga_g * (sv0 / spv0) * rd


def _msf_youd_2001_scalar(mw: float) -> float:
    """Youd et al. 2001 Magnitude Scaling Factor (Eq 24)."""
    if mw <= 0:
        return 1.0
    return 10 ** 2.24 / mw ** 2.56


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


def triggering_robertson_wride_1998(
    *,
    scenario: EarthquakeScenario,
    depth_m: Sequence[float],
    qtn: Sequence[float],
    ic: Sequence[float],
    sigma_v0_kpa: Sequence[float],
    sigma_prime_v0_kpa: Sequence[float],
    msf: float | None = None,
) -> LiquefactionProfile:
    """
    Run the full Robertson & Wride 1998 triggering pipeline.

    Args:
        scenario:            :class:`EarthquakeScenario` (magnitude,
                             pga, groundwater).
        depth_m:             depth array (m).
        qtn:                 Robertson 2009 Qtn array (dimensionless).
        ic:                  Robertson 2009 Ic array.
        sigma_v0_kpa:        total vertical stress (kPa).
        sigma_prime_v0_kpa:  effective vertical stress (kPa).
        msf:                 optional magnitude scaling factor override.
                             Defaults to Youd et al. 2001 on
                             ``scenario.magnitude_mw``.

    Returns:
        :class:`LiquefactionProfile` with per-depth CRR/CSR/FS and
        zone labels. ``extras`` carries ``Qtn_cs`` and ``rd`` for UI
        drill-down.
    """
    depth = np.asarray(depth_m, dtype=np.float64)
    qtn_arr = np.asarray(qtn, dtype=np.float64)
    ic_arr = np.asarray(ic, dtype=np.float64)
    sv0 = np.asarray(sigma_v0_kpa, dtype=np.float64)
    spv0 = np.asarray(sigma_prime_v0_kpa, dtype=np.float64)

    if not (depth.shape == qtn_arr.shape == ic_arr.shape == sv0.shape == spv0.shape):
        raise ValueError("all input arrays must share shape")

    kc = fines_correction_kc(ic_arr) if scenario.fines_correction else np.ones_like(ic_arr)
    qtn_cs = kc * qtn_arr
    crr_75 = crr_75_robertson_wride_1998(qtn_cs)

    msf_value = msf if msf is not None else _msf_youd_2001_scalar(scenario.magnitude_mw)
    rd = stress_reduction_liao_whitman_1986(depth)
    csr = csr_seed_idriss_1971(sv0, spv0, depth, scenario.pga_g)

    # FS = CRR * MSF / CSR
    with np.errstate(divide="ignore", invalid="ignore"):
        fs = np.where(csr > 1e-9, crr_75 * msf_value / csr, np.nan)

    # Clay cutoff: override FS to NaN where Ic > 2.6
    fs_final = np.where(ic_arr > CLAY_LIKE_IC_THRESHOLD, np.nan, fs)

    labels: list[LabelLiterals] = [
        _label_fs(float(f), float(i)) for f, i in zip(fs_final, ic_arr)
    ]

    return LiquefactionProfile(
        method="robertson_wride_1998",
        scenario=scenario,
        depth_m=depth,
        crr=crr_75,
        csr=csr,
        fs=fs_final,
        labels=labels,
        extras={
            "Qtn_cs": qtn_cs,
            "Kc": kc,
            "rd": rd,
            "msf": msf_value,
        },
    )
