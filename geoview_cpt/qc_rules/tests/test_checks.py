"""Tests for geoview_cpt.qc_rules.checks — Phase A-2 A2.6."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

from geoview_cpt.model import AcquisitionEvent, CPTChannel, CPTHeader, CPTSounding
from geoview_cpt.qc_rules.checks import (
    CHECK_REGISTRY,
    class_downgrade,
    depth_monotonic,
    drift_pore_class1,
    drift_sleeve_class1,
    drift_tip_class1,
    inclination_exceed,
    pore_max_reached,
    sensor_saturation,
    sleeve_max_reached,
    spike_detection,
    tip_max_reached,
    u2_response,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sounding(**channels) -> CPTSounding:
    s = CPTSounding(handle=1, element_tag="1", name="CPT-TEST")
    s.header = CPTHeader(sounding_id="CPT-TEST")
    for name, (unit, values) in channels.items():
        s.channels[name] = CPTChannel(name=name, unit=unit, values=values)
    return s


@pytest.fixture
def clean_sounding():
    depth = np.linspace(0.0, 20.0, 200)
    qc = np.linspace(0.5, 15.0, 200)          # MPa — smooth
    fs = np.linspace(5.0, 100.0, 200)          # kPa
    u2 = np.linspace(10.0, 200.0, 200)         # kPa — clearly varying
    incl = np.zeros(200) + 0.5
    return _make_sounding(
        depth=("m", depth),
        qc=("MPa", qc),
        fs=("kPa", fs),
        u2=("kPa", u2),
        incl=("deg", incl),
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_fourteen_entries(self):
        assert len(CHECK_REGISTRY) == 14

    def test_all_callable(self):
        for name, fn in CHECK_REGISTRY.items():
            assert callable(fn), f"{name} is not callable"


# ---------------------------------------------------------------------------
# basic_quality
# ---------------------------------------------------------------------------


class TestDepthMonotonic:
    def test_pass_on_clean(self, clean_sounding):
        assert depth_monotonic(clean_sounding) == []

    def test_flags_regression(self):
        s = _make_sounding(depth=("m", np.array([0.0, 0.1, 0.2, 0.15, 0.3])))
        issues = depth_monotonic(s)
        assert len(issues) == 1
        assert issues[0].severity == "critical"

    def test_missing_channel(self):
        s = CPTSounding(handle=1, element_tag="1")
        issues = depth_monotonic(s)
        assert len(issues) == 1
        assert "missing" in issues[0].description


class TestSpikeDetection:
    def test_pass_on_smooth_qc(self, clean_sounding):
        assert spike_detection(clean_sounding) == []

    def test_flags_big_delta(self):
        qc = np.array([1.0, 1.1, 1.2, 10.0, 10.1])
        s = _make_sounding(qc=("MPa", qc))
        issues = spike_detection(s)
        assert len(issues) >= 1
        assert issues[0].severity == "warning"


class TestSensorSaturation:
    def test_pass_when_under(self, clean_sounding):
        assert sensor_saturation(clean_sounding) == []

    def test_flags_qc_ceiling(self):
        qc = np.array([1.0, 80.0, 80.1, 2.0])
        s = _make_sounding(qc=("MPa", qc))
        issues = sensor_saturation(s)
        assert any("qc saturated" in i.description for i in issues)

    def test_flags_fs_ceiling(self):
        s = _make_sounding(fs=("kPa", np.array([10.0, 900.0, 15.0])))
        issues = sensor_saturation(s)
        assert any("fs saturated" in i.description for i in issues)

    def test_flags_u2_ceiling(self):
        s = _make_sounding(u2=("kPa", np.array([10.0, 5000.0, 100.0])))
        issues = sensor_saturation(s)
        assert any("u2 saturated" in i.description for i in issues)


class TestU2Response:
    def test_pass_on_varying_u2(self, clean_sounding):
        assert u2_response(clean_sounding) == []

    def test_flags_flat_u2(self):
        s = _make_sounding(u2=("kPa", np.full(100, 42.0)))
        issues = u2_response(s)
        assert len(issues) == 1
        assert "no variation" in issues[0].description

    def test_missing_channel(self):
        s = CPTSounding(handle=1, element_tag="1")
        issues = u2_response(s)
        assert len(issues) == 1


class TestInclinationExceed:
    def test_pass_at_low_angle(self, clean_sounding):
        assert inclination_exceed(clean_sounding) == []

    def test_flags_exceeds(self):
        s = _make_sounding(incl=("deg", np.array([0.0, 1.0, 2.5, 3.1])))
        issues = inclination_exceed(s)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert "3.10" in issues[0].description or "3.1" in issues[0].description


# ---------------------------------------------------------------------------
# termination
# ---------------------------------------------------------------------------


class TestTipMaxReached:
    def test_no_hit(self, clean_sounding):
        assert tip_max_reached(clean_sounding) == []

    def test_hit_emits_info(self):
        s = _make_sounding(qc=("MPa", np.array([10.0, 80.5])))
        issues = tip_max_reached(s)
        assert len(issues) == 1
        assert issues[0].severity == "info"


class TestSleeveAndPoreMax:
    def test_sleeve_hit(self):
        s = _make_sounding(fs=("kPa", np.array([10.0, 900.0])))
        assert len(sleeve_max_reached(s)) == 1

    def test_pore_hit(self):
        s = _make_sounding(u2=("kPa", np.array([10.0, 5000.0])))
        assert len(pore_max_reached(s)) == 1


# ---------------------------------------------------------------------------
# drift  (event-dependent)
# ---------------------------------------------------------------------------


class TestDriftStubbed:
    def test_without_events_returns_info(self, clean_sounding):
        # header has no events — stub returns a single "data gap" info
        for fn in (drift_tip_class1, drift_sleeve_class1, drift_pore_class1,
                   class_downgrade):
            issues = fn(clean_sounding)
            assert len(issues) == 1
            assert issues[0].severity == "info"
            assert "events" in issues[0].description.lower()

    def test_with_events_returns_empty(self, clean_sounding):
        clean_sounding.header.events.append(
            AcquisitionEvent(timestamp=datetime(2026, 4, 15), event_type="Deck Baseline")
        )
        # Populated events path exists and returns empty (real logic is A2.0b)
        assert drift_tip_class1(clean_sounding) == []
        assert class_downgrade(clean_sounding) == []
