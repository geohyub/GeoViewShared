"""Tests for geoview_cpt.seabed.landing_detection — Phase A-2 A2.13."""
from __future__ import annotations

import numpy as np
import pytest

from geoview_cpt.model import CPTChannel, CPTSounding
from geoview_cpt.seabed import (
    DEFAULT_LANDING_RULES,
    LandingResult,
    LandingRules,
    detect_seabed_landing,
)


def _sounding(**channels) -> CPTSounding:
    s = CPTSounding(handle=1, element_tag="1", name="CPT-TEST")
    for name, (unit, values) in channels.items():
        s.channels[name] = CPTChannel(name=name, unit=unit, values=np.asarray(values))
    return s


# ---------------------------------------------------------------------------
# Defaults + dataclass shape
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_default_rules(self):
        r = DEFAULT_LANDING_RULES
        assert r.k_required == 3
        assert r.qc_trigger_mpa == 0.3

    def test_rules_frozen(self):
        with pytest.raises(Exception):
            DEFAULT_LANDING_RULES.k_required = 2  # type: ignore


# ---------------------------------------------------------------------------
# Missing inputs
# ---------------------------------------------------------------------------


class TestMissingInputs:
    def test_no_depth_returns_empty(self):
        s = CPTSounding(handle=1, element_tag="1", name="x")
        r = detect_seabed_landing(s)
        assert r.detected is False
        assert r.available_count == 0

    def test_depth_only_gets_1_condition(self):
        s = _sounding(depth=("m", [0.0, 0.5, 1.0, 2.0]))
        r = detect_seabed_landing(s)
        # Only the depth_reached condition is available → k_required clipped
        assert r.available_count == 1
        assert r.k_required == 1
        assert r.detected is True


# ---------------------------------------------------------------------------
# Full 4-channel case
# ---------------------------------------------------------------------------


class TestFullChannels:
    def _rich(self) -> CPTSounding:
        depth = np.linspace(0.0, 1.0, 101)
        # Up to index 50 the frame is still falling: qc near zero, u2 flat
        qc = np.where(depth < 0.5, 0.05, 1.5)
        u2 = np.where(depth < 0.5, 10.0, 50.0)
        altimeter = np.where(depth < 0.5, 2.0, 0.2)
        return _sounding(
            depth=("m", depth),
            qc=("MPa", qc),
            u2=("kPa", u2),
            altimeter=("m", altimeter),
        )

    def test_detects_at_step(self):
        r = detect_seabed_landing(self._rich())
        assert r.detected is True
        assert r.depth_m is not None
        assert 0.45 <= r.depth_m <= 0.55
        assert r.available_count == 4
        assert r.k_satisfied >= 3

    def test_result_includes_all_conditions(self):
        r = detect_seabed_landing(self._rich())
        names = {c.name for c in r.conditions}
        assert names == {
            "depth_reached",
            "qc_excursion",
            "u2_jump",
            "altimeter_contact",
        }


# ---------------------------------------------------------------------------
# 3 channels (no altimeter) — 3-of-3
# ---------------------------------------------------------------------------


class TestAltimeterOptional:
    def test_three_channels_detects(self):
        depth = np.linspace(0.0, 1.0, 101)
        qc = np.where(depth < 0.5, 0.05, 1.0)
        u2 = np.where(depth < 0.5, 10.0, 50.0)
        s = _sounding(
            depth=("m", depth),
            qc=("MPa", qc),
            u2=("kPa", u2),
        )
        r = detect_seabed_landing(s)
        assert r.detected is True
        assert r.available_count == 3
        assert r.k_required == 3


# ---------------------------------------------------------------------------
# Noise floor / no-trigger case
# ---------------------------------------------------------------------------


class TestNoTrigger:
    def test_quiet_sounding_not_detected(self):
        depth = np.linspace(0.0, 1.0, 101)
        s = _sounding(
            depth=("m", depth),
            qc=("MPa", np.full(101, 0.01)),   # below trigger
            u2=("kPa", np.full(101, 10.0)),   # flat
            altimeter=("m", np.full(101, 3.0)),  # too far
        )
        r = detect_seabed_landing(s)
        # depth_reached still fires but not enough companions
        assert r.detected is False
        assert r.k_satisfied < r.k_required


# ---------------------------------------------------------------------------
# Custom rules override
# ---------------------------------------------------------------------------


class TestCustomRules:
    def test_lower_qc_threshold(self):
        depth = np.linspace(0.0, 1.0, 101)
        s = _sounding(
            depth=("m", depth),
            qc=("MPa", np.where(depth < 0.5, 0.05, 0.15)),
            u2=("kPa", np.where(depth < 0.5, 10.0, 50.0)),
        )
        relaxed = LandingRules(
            qc_trigger_mpa=0.1,
            u2_trigger_kpa=5.0,
            altimeter_trigger_m=0.5,
            min_search_depth_m=0.02,
            k_required=3,
            u2_baseline_samples=5,
        )
        r = detect_seabed_landing(s, rules=relaxed)
        assert r.detected is True

    def test_k_required_reduced_to_2(self):
        depth = np.linspace(0.0, 1.0, 101)
        s = _sounding(
            depth=("m", depth),
            qc=("MPa", np.where(depth < 0.5, 0.01, 0.5)),
            u2=("kPa", np.full(101, 10.0)),
            altimeter=("m", np.full(101, 3.0)),
        )
        rules = LandingRules(
            qc_trigger_mpa=0.3,
            u2_trigger_kpa=5.0,
            altimeter_trigger_m=0.5,
            min_search_depth_m=0.02,
            k_required=2,
            u2_baseline_samples=5,
        )
        r = detect_seabed_landing(s, rules=rules)
        assert r.detected is True
        assert r.k_required == 2
