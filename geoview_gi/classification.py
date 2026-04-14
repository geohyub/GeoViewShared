"""
geoview_gi.classification
================================
Geotechnical classification tables (Phase A-2 A2.17).

Codifies Tables 27-33 from the Wave 0 2nd-round HELMS reconnaissance so
every downstream report — 13-folder Deliverables Pack, CPT+Lab unified
log, borehole log, Korean rev7 — draws from a single source of truth.

Tables implemented:

 - **27** Undrained shear strength (``kPa``)          — ``classify_undrained_shear_strength``
 - **28** SPT N-value (blows/30 cm, sand)             — ``classify_spt_n``
 - **29** Relative density index Id (%, sand)         — ``classify_relative_density``
 - **30** Bedding thickness (``mm``)                  — ``classify_bedding_thickness``
 - **31** Discontinuity spacing (``mm``)              — ``classify_discontinuity_spacing``
 - **32** Particle shape (categorical lists)          — ``validate_particle_shape``
 - **33** Weathering grade (0-5)                      — ``classify_weathering``

Every numeric classifier returns the English label by default; pass
``korean=True`` (or call the ``_kr`` helper) to get the Korean label
from the master plan's rev7 style guide.

⚠️ Open Question 26 (Wave 0): HELMS Table 30 "bedding thickness" boundaries
are printed out of order in the source document. We encode the published
order with a ``boundary_anomaly`` marker so downstream QC can flag it and
a future correction stays auditable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "ClassificationRange",
    # Table 27
    "UNDRAINED_SHEAR_CLASSES",
    "UNDRAINED_SHEAR_LABELS_KR",
    "classify_undrained_shear_strength",
    "classify_undrained_shear_strength_kr",
    # Table 28
    "SPT_N_CLASSES",
    "SPT_N_LABELS_KR",
    "classify_spt_n",
    "classify_spt_n_kr",
    # Table 29
    "RELATIVE_DENSITY_CLASSES",
    "RELATIVE_DENSITY_LABELS_KR",
    "classify_relative_density",
    "classify_relative_density_kr",
    # Table 30
    "BEDDING_THICKNESS_CLASSES",
    "BEDDING_THICKNESS_LABELS_KR",
    "classify_bedding_thickness",
    "classify_bedding_thickness_kr",
    # Table 31
    "DISCONTINUITY_SPACING_CLASSES",
    "DISCONTINUITY_SPACING_LABELS_KR",
    "classify_discontinuity_spacing",
    "classify_discontinuity_spacing_kr",
    # Table 32
    "PARTICLE_SHAPE_ANGULARITY",
    "PARTICLE_SHAPE_FORM",
    "PARTICLE_SHAPE_SURFACE",
    "validate_particle_shape",
    # Table 33
    "WEATHERING_GRADES",
    "classify_weathering",
]


# ---------------------------------------------------------------------------
# Core type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassificationRange:
    """
    One half-open interval ``[min_val, max_val)`` used by every numeric table.

    ``max_val`` can be :data:`math.inf` for open-ended top buckets.
    The ``boundary_anomaly`` flag records Q26-style source-document issues
    so downstream QC can surface them to the user.
    """

    label: str
    min_val: float
    max_val: float
    boundary_anomaly: bool = False

    def contains(self, value: float) -> bool:
        if self.max_val == math.inf:
            return value >= self.min_val
        return self.min_val <= value < self.max_val


def _classify(
    value: float,
    buckets: list[ClassificationRange],
) -> str:
    for b in buckets:
        if b.contains(value):
            return b.label
    return "N/A"


def _kr(label: str, kr_map: dict[str, str]) -> str:
    return kr_map.get(label, label)


# ---------------------------------------------------------------------------
# Table 27 — Undrained Shear Strength (kPa)
# ---------------------------------------------------------------------------


UNDRAINED_SHEAR_CLASSES: list[ClassificationRange] = [
    ClassificationRange("Extremely low",     0.0,  10.0),
    ClassificationRange("Very low",         10.0,  20.0),
    ClassificationRange("Low",              20.0,  40.0),
    ClassificationRange("Medium",           40.0,  75.0),
    ClassificationRange("High",             75.0, 150.0),
    ClassificationRange("Very High",       150.0, 300.0),
    ClassificationRange("Extremely High",  300.0, math.inf),
]


UNDRAINED_SHEAR_LABELS_KR: dict[str, str] = {
    "Extremely low":  "매우 연약",
    "Very low":       "연약",
    "Low":            "연한",
    "Medium":         "보통",
    "High":           "견고한",
    "Very High":      "매우 견고",
    "Extremely High": "극히 견고",
}


def classify_undrained_shear_strength(su_kpa: float) -> str:
    """Table 27 — English label for ``su`` in kPa."""
    return _classify(su_kpa, UNDRAINED_SHEAR_CLASSES)


def classify_undrained_shear_strength_kr(su_kpa: float) -> str:
    """Table 27 — Korean label for ``su`` in kPa."""
    return _kr(classify_undrained_shear_strength(su_kpa), UNDRAINED_SHEAR_LABELS_KR)


# ---------------------------------------------------------------------------
# Table 28 — SPT N-value (sand)
# ---------------------------------------------------------------------------


SPT_N_CLASSES: list[ClassificationRange] = [
    ClassificationRange("Very Loose",   0.0,   4.0),
    ClassificationRange("Loose",        4.0,  10.0),
    ClassificationRange("Medium Dense",10.0,  30.0),
    ClassificationRange("Dense",       30.0,  50.0),
    ClassificationRange("Very Dense",  50.0, math.inf),
]


SPT_N_LABELS_KR: dict[str, str] = {
    "Very Loose":   "매우 느슨",
    "Loose":        "느슨",
    "Medium Dense": "보통 조밀",
    "Dense":        "조밀",
    "Very Dense":   "매우 조밀",
}


def classify_spt_n(n_value: float) -> str:
    return _classify(n_value, SPT_N_CLASSES)


def classify_spt_n_kr(n_value: float) -> str:
    return _kr(classify_spt_n(n_value), SPT_N_LABELS_KR)


# ---------------------------------------------------------------------------
# Table 29 — Relative Density Index Id (%)
# ---------------------------------------------------------------------------


RELATIVE_DENSITY_CLASSES: list[ClassificationRange] = [
    ClassificationRange("Very Loose",    0.0,  15.0),
    ClassificationRange("Loose",        15.0,  35.0),
    ClassificationRange("Medium Dense", 35.0,  65.0),
    ClassificationRange("Dense",        65.0,  85.0),
    ClassificationRange("Very Dense",   85.0, 100.0 + 1e-9),  # include 100%
]


RELATIVE_DENSITY_LABELS_KR: dict[str, str] = SPT_N_LABELS_KR


def classify_relative_density(id_pct: float) -> str:
    return _classify(id_pct, RELATIVE_DENSITY_CLASSES)


def classify_relative_density_kr(id_pct: float) -> str:
    return _kr(classify_relative_density(id_pct), RELATIVE_DENSITY_LABELS_KR)


# ---------------------------------------------------------------------------
# Table 30 — Bedding Thickness (mm)
# ---------------------------------------------------------------------------
#
# Q26: HELMS printed boundaries are out of order. We preserve the published
# numbers verbatim and flag the lowest bucket with ``boundary_anomaly=True``
# so the QC layer (A2.6) can raise a note for the reviewer.
#


BEDDING_THICKNESS_CLASSES: list[ClassificationRange] = [
    ClassificationRange("Very Thinly Bedded",    0.0,    10.0, boundary_anomaly=True),
    ClassificationRange("Thinly Bedded",        10.0,    30.0),
    ClassificationRange("Medium Bedded",        30.0,   100.0),
    ClassificationRange("Thickly Bedded",      100.0,   300.0),
    ClassificationRange("Very Thickly Bedded", 300.0,  1000.0),
    ClassificationRange("Massive",            1000.0, math.inf),
]


BEDDING_THICKNESS_LABELS_KR: dict[str, str] = {
    "Very Thinly Bedded":  "매우 얇은 성층",
    "Thinly Bedded":       "얇은 성층",
    "Medium Bedded":       "중간 성층",
    "Thickly Bedded":      "두꺼운 성층",
    "Very Thickly Bedded": "매우 두꺼운 성층",
    "Massive":             "괴상",
}


def classify_bedding_thickness(thickness_mm: float) -> str:
    return _classify(thickness_mm, BEDDING_THICKNESS_CLASSES)


def classify_bedding_thickness_kr(thickness_mm: float) -> str:
    return _kr(classify_bedding_thickness(thickness_mm), BEDDING_THICKNESS_LABELS_KR)


# ---------------------------------------------------------------------------
# Table 31 — Discontinuity Spacing (mm)
# ---------------------------------------------------------------------------


DISCONTINUITY_SPACING_CLASSES: list[ClassificationRange] = [
    ClassificationRange("Extremely Close",   0.0,    20.0),
    ClassificationRange("Very Close",       20.0,    60.0),
    ClassificationRange("Close",            60.0,   200.0),
    ClassificationRange("Moderate",        200.0,   600.0),
    ClassificationRange("Wide",            600.0,  2000.0),
    ClassificationRange("Very Wide",      2000.0,  6000.0),
    ClassificationRange("Extremely Wide", 6000.0, math.inf),
]


DISCONTINUITY_SPACING_LABELS_KR: dict[str, str] = {
    "Extremely Close": "극히 근접",
    "Very Close":      "매우 근접",
    "Close":           "근접",
    "Moderate":        "중간",
    "Wide":            "넓음",
    "Very Wide":       "매우 넓음",
    "Extremely Wide":  "극히 넓음",
}


def classify_discontinuity_spacing(spacing_mm: float) -> str:
    return _classify(spacing_mm, DISCONTINUITY_SPACING_CLASSES)


def classify_discontinuity_spacing_kr(spacing_mm: float) -> str:
    return _kr(
        classify_discontinuity_spacing(spacing_mm),
        DISCONTINUITY_SPACING_LABELS_KR,
    )


# ---------------------------------------------------------------------------
# Table 32 — Particle Shape (categorical)
# ---------------------------------------------------------------------------


PARTICLE_SHAPE_ANGULARITY: tuple[str, ...] = (
    "Very angular",
    "Angular",
    "Subangular",
    "Subrounded",
    "Rounded",
    "Well Rounded",
)

PARTICLE_SHAPE_FORM: tuple[str, ...] = ("Cubic", "Flat", "Elongate")

PARTICLE_SHAPE_SURFACE: tuple[str, ...] = ("Rough", "Smooth")


ParticleShapeAxis = Literal["angularity", "form", "surface"]


def validate_particle_shape(axis: ParticleShapeAxis, label: str) -> bool:
    """
    Return True when ``label`` is a valid entry on the requested Table 32
    axis. Use ``validate_particle_shape("angularity", "Subrounded")`` etc.
    """
    pool = {
        "angularity": PARTICLE_SHAPE_ANGULARITY,
        "form": PARTICLE_SHAPE_FORM,
        "surface": PARTICLE_SHAPE_SURFACE,
    }.get(axis)
    if pool is None:
        raise ValueError(f"unknown particle-shape axis {axis!r}")
    return label in pool


# ---------------------------------------------------------------------------
# Table 33 — Weathering Grade (0-5)
# ---------------------------------------------------------------------------


WEATHERING_GRADES: dict[int, tuple[str, str]] = {
    0: ("Fresh",                "No visible sign of rock weathering"),
    1: ("Slightly Weathered",   "Discoloration on discontinuity surfaces"),
    2: ("Moderately Weathered", "< 50% decomposed"),
    3: ("Highly Weathered",     "> 50% decomposed"),
    4: ("Completely Weathered", "All decomposed to soil; structure intact"),
    5: ("Residual Soil",        "All converted to soil; structure destroyed"),
}


def classify_weathering(grade: int) -> tuple[str, str]:
    """Return ``(label, description)`` for a weathering grade 0-5."""
    return WEATHERING_GRADES.get(grade, ("Unknown", ""))
