"""
geoview_cpt.derivation
================================
CPT derived-channel calculators (Phase A-2 A2.5b).

Public API:

    rf       compute_rf — Eq 3 friction ratio (%)
    bq       compute_bq — Eq 4 normalized pore-pressure parameter
    ic       compute_qt_normalized, compute_fr_normalized, compute_ic
              — Robertson & Wride 1998 normalized Qt / Fr / Ic
    sbt      classify_robertson_1990 — 9-zone soil behaviour type
    gamma    estimate_gamma_robertson_cabal_2010 — γ from qt and Rf

Every function is unit-aware (routes pressure inputs through
:func:`geoview_cpt.correction.units.to_mpa` / :func:`to_kpa`) and
returns a :class:`geoview_cpt.model.CPTChannel`.
"""
from __future__ import annotations

from geoview_cpt.derivation.bq import compute_bq
from geoview_cpt.derivation.gamma import estimate_gamma_robertson_cabal_2010
from geoview_cpt.derivation.qtn import (
    QtnIterationResult,
    compute_ic_robertson_2009,
    compute_qtn_iterative,
)
from geoview_cpt.derivation.ic import (
    compute_fr_normalized,
    compute_ic,
    compute_qt_normalized,
)
from geoview_cpt.derivation.rf import compute_rf
from geoview_cpt.derivation.sbt import (
    ROBERTSON_1990_ZONES,
    classify_ic_to_robertson_1990_zone,
    classify_robertson_1990,
)
from geoview_cpt.derivation.strength import (
    DEFAULT_NKT,
    compute_dr_jamiolkowski,
    compute_su,
)
from geoview_cpt.derivation.water_content import compute_water_content

__all__ = [
    "compute_rf",
    "compute_bq",
    "compute_qt_normalized",
    "compute_fr_normalized",
    "compute_ic",
    "classify_robertson_1990",
    "classify_ic_to_robertson_1990_zone",
    "ROBERTSON_1990_ZONES",
    "estimate_gamma_robertson_cabal_2010",
    "compute_su",
    "compute_dr_jamiolkowski",
    "DEFAULT_NKT",
    "compute_water_content",
    "compute_qtn_iterative",
    "compute_ic_robertson_2009",
    "QtnIterationResult",
]
