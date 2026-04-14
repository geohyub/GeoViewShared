"""Tests for geoview_gi.minimal_model — Phase A-2 A2.19."""
from __future__ import annotations

from dataclasses import fields

import pytest

from geoview_gi.minimal_model import (
    Borehole,
    LabSample,
    SPTTest,
    StratumLayer,
)


# ---------------------------------------------------------------------------
# Borehole
# ---------------------------------------------------------------------------


class TestBorehole:
    def test_minimal(self):
        b = Borehole(loca_id="BH-01")
        assert b.loca_id == "BH-01"
        assert b.strata == []
        assert b.spt_tests == []
        assert b.samples == []
        assert b.total_strata == 0

    def test_empty_loca_id_rejected(self):
        with pytest.raises(ValueError, match="loca_id"):
            Borehole(loca_id="")

    def test_add_stratum(self):
        b = Borehole(loca_id="BH-01")
        b.add_stratum(StratumLayer(top_m=0, base_m=2.5, description="Sand"))
        b.add_stratum(StratumLayer(top_m=2.5, base_m=5, description="Clay"))
        assert b.total_strata == 2
        assert b.strata[1].thickness_m == 2.5

    def test_add_stratum_rejects_inverted(self):
        b = Borehole(loca_id="BH-01")
        with pytest.raises(ValueError):
            b.add_stratum(StratumLayer(top_m=5, base_m=2))

    def test_add_spt_and_sample(self):
        b = Borehole(loca_id="BH-01")
        b.add_spt(SPTTest(top_m=3.0, main_blows=25))
        b.add_sample(LabSample(loca_id="BH-01", sample_id="S1", top_m=3.0))
        assert len(b.spt_tests) == 1
        assert len(b.samples) == 1


# ---------------------------------------------------------------------------
# StratumLayer
# ---------------------------------------------------------------------------


class TestStratumLayer:
    def test_thickness_and_midpoint(self):
        s = StratumLayer(top_m=10, base_m=15)
        assert s.thickness_m == 5
        assert s.midpoint_m == 12.5

    def test_negative_top_rejected(self):
        with pytest.raises(ValueError, match="top_m"):
            StratumLayer(top_m=-1, base_m=2)

    def test_inverted_rejected(self):
        with pytest.raises(ValueError, match="base_m"):
            StratumLayer(top_m=5, base_m=5)

    def test_weathering_grade_range(self):
        StratumLayer(top_m=0, base_m=1, weathering_grade=0)
        StratumLayer(top_m=0, base_m=1, weathering_grade=5)
        with pytest.raises(ValueError):
            StratumLayer(top_m=0, base_m=1, weathering_grade=6)

    def test_weathering_grade_none_allowed(self):
        s = StratumLayer(top_m=0, base_m=1)
        assert s.weathering_grade is None


# ---------------------------------------------------------------------------
# SPTTest
# ---------------------------------------------------------------------------


class TestSPTTest:
    def test_n_value_inferred_from_main(self):
        t = SPTTest(top_m=3.0, main_blows=30)
        assert t.n_value == 30

    def test_explicit_n_value_wins(self):
        t = SPTTest(top_m=3.0, main_blows=30, n_value=50)
        assert t.n_value == 50

    def test_refusal_flag(self):
        t = SPTTest(top_m=6.0, refusal=True)
        assert t.refusal is True

    def test_negative_depth_rejected(self):
        with pytest.raises(ValueError):
            SPTTest(top_m=-1)


# ---------------------------------------------------------------------------
# LabSample — 17-field contract
# ---------------------------------------------------------------------------


class TestLabSampleContract:
    def test_has_17_fields(self):
        """Contract guard: LabSample must stay at exactly 17 public fields."""
        public = [f for f in fields(LabSample) if not f.name.startswith("_")]
        assert len(public) == 17, (
            f"LabSample must have 17 fields, found {len(public)}: "
            f"{[f.name for f in public]}"
        )

    def test_field_groups(self):
        """Names are stable contract for AGS4 mapping."""
        names = {f.name for f in fields(LabSample)}
        expected = {
            # identity (4)
            "loca_id", "sample_id", "sample_type", "sample_ref",
            # depth (3)
            "top_m", "base_m", "recovery_pct",
            # state (3)
            "moisture_content_pct", "bulk_density_t_m3", "void_ratio",
            # index (3)
            "liquid_limit_pct", "plastic_limit_pct", "fines_pct",
            # strength (3)
            "undrained_shear_strength_kpa",
            "effective_friction_angle_deg",
            "effective_cohesion_kpa",
            # failure (1)
            "failure_code",
        }
        assert names == expected


class TestLabSampleValidation:
    def test_minimal(self):
        s = LabSample(loca_id="BH-01", sample_id="U1")
        assert s.sample_type == "OTHER"
        assert s.failure_code == "N/A"
        assert s.base_m is None

    def test_empty_ids_rejected(self):
        with pytest.raises(ValueError, match="loca_id"):
            LabSample(loca_id="", sample_id="U1")
        with pytest.raises(ValueError, match="sample_id"):
            LabSample(loca_id="BH-01", sample_id="")

    def test_negative_top_rejected(self):
        with pytest.raises(ValueError, match="top_m"):
            LabSample(loca_id="BH-01", sample_id="S1", top_m=-1)

    def test_base_before_top_rejected(self):
        with pytest.raises(ValueError, match="base_m"):
            LabSample(loca_id="BH-01", sample_id="S1", top_m=5, base_m=3)

    def test_recovery_range(self):
        LabSample(loca_id="BH-01", sample_id="S1", recovery_pct=0)
        LabSample(loca_id="BH-01", sample_id="S1", recovery_pct=100)
        with pytest.raises(ValueError, match="recovery_pct"):
            LabSample(loca_id="BH-01", sample_id="S1", recovery_pct=150)

    def test_strength_slots_optional(self):
        s = LabSample(loca_id="BH-01", sample_id="S1")
        assert s.undrained_shear_strength_kpa is None
        assert s.effective_friction_angle_deg is None
        assert s.effective_cohesion_kpa is None

    def test_populated_example(self):
        s = LabSample(
            loca_id="BH-01",
            sample_id="U1",
            sample_type="U",
            top_m=3.0,
            base_m=3.6,
            recovery_pct=95.0,
            moisture_content_pct=28.5,
            undrained_shear_strength_kpa=45.2,
            failure_code="A",
        )
        assert s.sample_type == "U"
        assert s.failure_code == "A"
