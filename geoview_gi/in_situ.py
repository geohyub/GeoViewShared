"""
geoview_gi.in_situ
================================
Lateral Load Test / Pressuremeter (LLT) data model + formulas.

Wave 0 catalog §6.1 pins the six pressure-correction and modulus
equations used throughout the GeoView rev7 부록6 deliverable:

    Pe = P + P_s − P_G                     effective pressure
    Py = Py' − P_o                          yield pressure (corrected)
    Pl = Pl' − P_o                          limit pressure (corrected)
    Km = (Py' − P_o) / (r_y − r_o)          modulus of reaction
    Rm = (r_o + r_y) / 2                    mean radius during expansion
    Em = (1 + ν) × Rm × Km                  pressuremeter modulus

where
 - ``P``   raw applied pressure
 - ``P_s`` static (standing water) correction
 - ``P_G`` probe calibration correction
 - ``P_o`` at-rest earth pressure (shifts Py'/Pl' to effective stress)
 - ``r_o`` initial probe radius
 - ``r_y`` probe radius at yield point
 - ``ν``   drained Poisson's ratio (default 0.45 — Wave 0 catalog)

Wave 0 3rd-round confirmed a golden sample on YW-1 / depth 3.0 m /
2025-04 with ``Em = 1.34 MPa``. The test suite reproduces this value
from the intermediate quantities as a regression guard.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable

import numpy as np

__all__ = [
    "LLTTest",
    "DEFAULT_POISSON",
    "compute_pe",
    "compute_py",
    "compute_pl",
    "compute_km",
    "compute_rm",
    "compute_em",
]


DEFAULT_POISSON: float = 0.45
"""Drained Poisson's ratio default used when the rev7 report omits ν."""


# ---------------------------------------------------------------------------
# Formulas — all scalars accept numpy arrays too
# ---------------------------------------------------------------------------


def compute_pe(
    p: float | np.ndarray,
    p_s: float | np.ndarray,
    p_g: float | np.ndarray,
) -> float | np.ndarray:
    """Effective applied pressure ``Pe = P + P_s − P_G``."""
    return p + p_s - p_g


def compute_py(py_raw: float, p_o: float) -> float:
    """Yield pressure ``Py = Py' − P_o``."""
    return py_raw - p_o


def compute_pl(pl_raw: float, p_o: float) -> float:
    """Limit pressure ``Pl = Pl' − P_o``."""
    return pl_raw - p_o


def compute_km(py_raw: float, p_o: float, r_y: float, r_o: float) -> float:
    """
    Modulus of reaction ``Km = (Py' − P_o) / (r_y − r_o)``.

    Both radii must use the same length unit; the return value carries
    the pressure unit divided by the radius unit (e.g. MPa / m).
    """
    dr = r_y - r_o
    if abs(dr) < 1e-12:
        raise ValueError("r_y and r_o are equal — cannot compute Km")
    return (py_raw - p_o) / dr


def compute_rm(r_o: float, r_y: float) -> float:
    """Mean radius during expansion ``Rm = (r_o + r_y) / 2``."""
    return 0.5 * (r_o + r_y)


def compute_em(
    py_raw: float,
    p_o: float,
    r_o: float,
    r_y: float,
    *,
    nu: float = DEFAULT_POISSON,
) -> float:
    """
    Pressuremeter modulus ``Em = (1 + ν) × Rm × Km``.

    Unit sanity: if ``Py'``, ``P_o`` are in kPa and ``r_o``, ``r_y`` in
    metres, then ``Km`` is ``kPa/m``, ``Rm`` is ``m``, and ``Em`` ends
    up in ``kPa``. Convert upstream if you want MPa.
    """
    km = compute_km(py_raw, p_o, r_y, r_o)
    rm = compute_rm(r_o, r_y)
    return (1.0 + nu) * rm * km


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class LLTTest:
    """
    One Lateral Load / Pressuremeter test point.

    Only the fields the rev7 deliverable actually reports are captured;
    downstream tools can stash extras in :attr:`metadata`.
    """

    borehole_id: str
    depth_m: float
    test_date: date | None = None
    py_raw_kpa: float = 0.0
    pl_raw_kpa: float = 0.0
    p_o_kpa: float = 0.0
    r_o_mm: float = 0.0
    r_y_mm: float = 0.0
    nu: float = DEFAULT_POISSON
    source_report_path: Path | None = None
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # derived
    # ------------------------------------------------------------------

    @property
    def py_kpa(self) -> float:
        return compute_py(self.py_raw_kpa, self.p_o_kpa)

    @property
    def pl_kpa(self) -> float:
        return compute_pl(self.pl_raw_kpa, self.p_o_kpa)

    @property
    def km_kpa_per_m(self) -> float:
        # Radii from mm to m so Km carries kPa/m
        return compute_km(
            self.py_raw_kpa,
            self.p_o_kpa,
            self.r_y_mm / 1000.0,
            self.r_o_mm / 1000.0,
        )

    @property
    def rm_m(self) -> float:
        return compute_rm(self.r_o_mm / 1000.0, self.r_y_mm / 1000.0)

    @property
    def em_mpa(self) -> float:
        em_kpa = compute_em(
            self.py_raw_kpa,
            self.p_o_kpa,
            self.r_o_mm / 1000.0,
            self.r_y_mm / 1000.0,
            nu=self.nu,
        )
        return em_kpa / 1000.0
