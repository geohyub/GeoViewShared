"""Tests for geoview_gi.classification — Phase A-2 A2.17."""
from __future__ import annotations

import math

import pytest

from geoview_gi.classification import (
    BEDDING_THICKNESS_CLASSES,
    DISCONTINUITY_SPACING_CLASSES,
    PARTICLE_SHAPE_ANGULARITY,
    PARTICLE_SHAPE_FORM,
    PARTICLE_SHAPE_SURFACE,
    RELATIVE_DENSITY_CLASSES,
    SPT_N_CLASSES,
    UNDRAINED_SHEAR_CLASSES,
    WEATHERING_GRADES,
    ClassificationRange,
    classify_bedding_thickness,
    classify_bedding_thickness_kr,
    classify_discontinuity_spacing,
    classify_discontinuity_spacing_kr,
    classify_relative_density,
    classify_relative_density_kr,
    classify_spt_n,
    classify_spt_n_kr,
    classify_undrained_shear_strength,
    classify_undrained_shear_strength_kr,
    classify_weathering,
    validate_particle_shape,
)


# ---------------------------------------------------------------------------
# ClassificationRange
# ---------------------------------------------------------------------------


class TestClassificationRange:
    def test_contains_half_open(self):
        r = ClassificationRange("x", 10, 20)
        assert r.contains(10)
        assert r.contains(19.999)
        assert not r.contains(20)  # half-open top

    def test_open_top(self):
        r = ClassificationRange("top", 300, math.inf)
        assert r.contains(1_000_000)
        assert r.contains(300)

    def test_boundary_anomaly_flag(self):
        r = ClassificationRange("x", 0, 1, boundary_anomaly=True)
        assert r.boundary_anomaly is True


# ---------------------------------------------------------------------------
# Table 27 — Undrained shear strength
# ---------------------------------------------------------------------------


class TestUndrainedShearStrength:
    @pytest.mark.parametrize(
        "su, label",
        [
            (0,    "Extremely low"),
            (5,    "Extremely low"),
            (10,   "Very low"),
            (20,   "Low"),
            (40,   "Medium"),
            (75,   "High"),
            (150,  "Very High"),
            (300,  "Extremely High"),
            (1000, "Extremely High"),
        ],
    )
    def test_english_labels(self, su, label):
        assert classify_undrained_shear_strength(su) == label

    def test_korean_labels(self):
        assert classify_undrained_shear_strength_kr(5) == "매우 연약"
        assert classify_undrained_shear_strength_kr(40) == "보통"
        assert classify_undrained_shear_strength_kr(400) == "극히 견고"

    def test_all_seven_buckets_present(self):
        assert len(UNDRAINED_SHEAR_CLASSES) == 7
        labels = [c.label for c in UNDRAINED_SHEAR_CLASSES]
        assert labels[0] == "Extremely low"
        assert labels[-1] == "Extremely High"

    def test_boundary_epsilon(self):
        # values right below a boundary should return lower class
        assert classify_undrained_shear_strength(9.999) == "Extremely low"
        assert classify_undrained_shear_strength(10.0) == "Very low"


# ---------------------------------------------------------------------------
# Table 28 — SPT N
# ---------------------------------------------------------------------------


class TestSptN:
    @pytest.mark.parametrize(
        "n, label",
        [(0, "Very Loose"), (3, "Very Loose"), (4, "Loose"),
         (10, "Medium Dense"), (30, "Dense"), (50, "Very Dense"), (99, "Very Dense")],
    )
    def test_english(self, n, label):
        assert classify_spt_n(n) == label

    def test_korean(self):
        assert classify_spt_n_kr(25) == "보통 조밀"
        assert classify_spt_n_kr(50) == "매우 조밀"

    def test_five_buckets(self):
        assert len(SPT_N_CLASSES) == 5


# ---------------------------------------------------------------------------
# Table 29 — Relative Density
# ---------------------------------------------------------------------------


class TestRelativeDensity:
    @pytest.mark.parametrize(
        "id_pct, label",
        [(0, "Very Loose"), (15, "Loose"), (35, "Medium Dense"),
         (65, "Dense"), (85, "Very Dense"), (100, "Very Dense")],
    )
    def test_english(self, id_pct, label):
        assert classify_relative_density(id_pct) == label

    def test_korean(self):
        assert classify_relative_density_kr(50) == "보통 조밀"


# ---------------------------------------------------------------------------
# Table 30 — Bedding Thickness (with Q26 anomaly)
# ---------------------------------------------------------------------------


class TestBeddingThickness:
    @pytest.mark.parametrize(
        "thk, label",
        [(5, "Very Thinly Bedded"),
         (10, "Thinly Bedded"),
         (30, "Medium Bedded"),
         (100, "Thickly Bedded"),
         (300, "Very Thickly Bedded"),
         (1000, "Massive"),
         (5000, "Massive")],
    )
    def test_english(self, thk, label):
        assert classify_bedding_thickness(thk) == label

    def test_korean(self):
        assert classify_bedding_thickness_kr(500) == "매우 두꺼운 성층"

    def test_q26_anomaly_flag_present(self):
        """Table 30 lowest bucket carries the boundary-anomaly marker."""
        flagged = [c for c in BEDDING_THICKNESS_CLASSES if c.boundary_anomaly]
        assert len(flagged) == 1
        assert flagged[0].label == "Very Thinly Bedded"


# ---------------------------------------------------------------------------
# Table 31 — Discontinuity Spacing
# ---------------------------------------------------------------------------


class TestDiscontinuitySpacing:
    @pytest.mark.parametrize(
        "mm, label",
        [(10, "Extremely Close"), (60, "Close"), (200, "Moderate"),
         (600, "Wide"), (2000, "Very Wide"), (10_000, "Extremely Wide")],
    )
    def test_english(self, mm, label):
        assert classify_discontinuity_spacing(mm) == label

    def test_korean(self):
        assert classify_discontinuity_spacing_kr(500) == "중간"
        assert classify_discontinuity_spacing_kr(10_000) == "극히 넓음"

    def test_seven_buckets(self):
        assert len(DISCONTINUITY_SPACING_CLASSES) == 7


# ---------------------------------------------------------------------------
# Table 32 — Particle Shape
# ---------------------------------------------------------------------------


class TestParticleShape:
    def test_angularity_list(self):
        assert "Subrounded" in PARTICLE_SHAPE_ANGULARITY
        assert "Well Rounded" in PARTICLE_SHAPE_ANGULARITY
        assert len(PARTICLE_SHAPE_ANGULARITY) == 6

    def test_form_list(self):
        assert set(PARTICLE_SHAPE_FORM) == {"Cubic", "Flat", "Elongate"}

    def test_surface_list(self):
        assert set(PARTICLE_SHAPE_SURFACE) == {"Rough", "Smooth"}

    def test_validate_angularity(self):
        assert validate_particle_shape("angularity", "Subrounded")
        assert not validate_particle_shape("angularity", "Spiky")

    def test_validate_form(self):
        assert validate_particle_shape("form", "Cubic")

    def test_validate_surface(self):
        assert validate_particle_shape("surface", "Rough")

    def test_unknown_axis_raises(self):
        with pytest.raises(ValueError, match="axis"):
            validate_particle_shape("color", "red")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Table 33 — Weathering Grade
# ---------------------------------------------------------------------------


class TestWeathering:
    def test_all_six_grades(self):
        assert set(WEATHERING_GRADES.keys()) == {0, 1, 2, 3, 4, 5}

    @pytest.mark.parametrize(
        "grade, label",
        [(0, "Fresh"), (1, "Slightly Weathered"),
         (2, "Moderately Weathered"), (3, "Highly Weathered"),
         (4, "Completely Weathered"), (5, "Residual Soil")],
    )
    def test_labels(self, grade, label):
        assert classify_weathering(grade)[0] == label

    def test_descriptions_nonempty(self):
        for grade in range(6):
            _, desc = classify_weathering(grade)
            assert len(desc) > 0

    def test_unknown_grade(self):
        label, desc = classify_weathering(99)
        assert label == "Unknown"
        assert desc == ""
