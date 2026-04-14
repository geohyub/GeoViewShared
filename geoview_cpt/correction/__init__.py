"""
geoview_cpt.correction
================================
CPT raw-channel correction primitives (Phase A-2 A2.5a).

Public API:

    units      _to_mpa, _to_kpa, UnitError
    qt         compute_qt — Eq 1 (Lunne et al. 1997)
    u0         hydrostatic_pressure
    stress     compute_sigma_v0, compute_sigma_prime_v0

All functions consume :class:`geoview_cpt.model.CPTChannel` instances and
return new :class:`CPTChannel` instances. Inputs are unit-aware: parsers
ship ``qc`` in MPa and ``fs``/``u2`` in kPa (Week 3 contract), so every
deriver routes pressure inputs through :func:`units._to_mpa` /
:func:`units._to_kpa` before applying the formula.
"""
from __future__ import annotations

from geoview_cpt.correction.qt import compute_qt
from geoview_cpt.correction.stress import (
    compute_sigma_prime_v0,
    compute_sigma_v0,
)
from geoview_cpt.correction.u0 import hydrostatic_pressure
from geoview_cpt.correction.units import UnitError, to_kpa, to_mpa

__all__ = [
    "UnitError",
    "to_mpa",
    "to_kpa",
    "compute_qt",
    "hydrostatic_pressure",
    "compute_sigma_v0",
    "compute_sigma_prime_v0",
]
