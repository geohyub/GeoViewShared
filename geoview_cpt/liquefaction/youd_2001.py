"""
geoview_cpt.liquefaction.youd_2001
================================
Youd et al. (2001) NCEER workshop CPT-based triggering.

Reference: Youd T.L. et al. (2001) "Liquefaction resistance of soils",
J. Geotech. Geoenviron. Eng. 127(10).

Differences from Robertson & Wride 1998:

 - CRR_7.5 equation is the same (R&W 1998 Eq 10a/10b) — Youd 2001
   endorsed R&W 1998 as the standard CPT method at the NCEER
   workshop. The main change is the **Magnitude Scaling Factor**
   formalisation:

        MSF = 10^2.24 / Mw^2.56            (upper bound, clean sand)
        MSF_lower = (Mw / 7.5)^(−2.56)     (lower bound)

 - rd profile stays Liao & Whitman 1986 (shared via
   :mod:`robertson_wride_1998`).

This module therefore reuses the R&W 1998 CRR computation and only
swaps the MSF. :func:`msf_youd_2001` returns the upper-bound curve
by default; pass ``upper_bound=False`` for the lower bound.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from geoview_cpt.liquefaction.common import (
    EarthquakeScenario,
    LiquefactionProfile,
)
from geoview_cpt.liquefaction.robertson_wride_1998 import (
    triggering_robertson_wride_1998,
)

__all__ = ["msf_youd_2001", "triggering_youd_2001"]


def msf_youd_2001(mw: float, *, upper_bound: bool = True) -> float:
    """
    Magnitude Scaling Factor per Youd et al. 2001 Eq 24 (upper) or Eq 25 (lower).
    """
    if mw <= 0:
        raise ValueError(f"mw must be positive, got {mw}")
    if upper_bound:
        return 10 ** 2.24 / mw ** 2.56
    return (mw / 7.5) ** -2.56


def triggering_youd_2001(
    *,
    scenario: EarthquakeScenario,
    depth_m: Sequence[float],
    qtn: Sequence[float],
    ic: Sequence[float],
    sigma_v0_kpa: Sequence[float],
    sigma_prime_v0_kpa: Sequence[float],
    upper_bound: bool = True,
) -> LiquefactionProfile:
    """
    Run Youd et al. 2001 triggering — identical to R&W 1998 except for
    the MSF variant (upper vs lower bound curve).
    """
    msf = msf_youd_2001(scenario.magnitude_mw, upper_bound=upper_bound)
    profile = triggering_robertson_wride_1998(
        scenario=scenario,
        depth_m=depth_m,
        qtn=qtn,
        ic=ic,
        sigma_v0_kpa=sigma_v0_kpa,
        sigma_prime_v0_kpa=sigma_prime_v0_kpa,
        msf=msf,
    )
    return LiquefactionProfile(
        method="youd_2001" + ("_upper" if upper_bound else "_lower"),
        scenario=scenario,
        depth_m=profile.depth_m,
        crr=profile.crr,
        csr=profile.csr,
        fs=profile.fs,
        labels=profile.labels,
        extras={**profile.extras, "msf_variant": "upper" if upper_bound else "lower"},
    )
