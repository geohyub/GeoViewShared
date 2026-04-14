"""Tests for geoview_cpt.model channel + header — Phase A-2 A2.1."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from geoview_cpt.model import (
    AcquisitionEvent,
    CPTChannel,
    CPTHeader,
    CPTProject,
    CPTSounding,
)
from geoview_gi.minimal_model import StratumLayer


# ---------------------------------------------------------------------------
# CPTChannel
# ---------------------------------------------------------------------------


class TestCPTChannel:
    def test_default_empty(self):
        c = CPTChannel(name="qc")
        assert c.name == "qc"
        assert c.unit == ""
        assert c.is_empty
        assert len(c) == 0

    def test_with_values(self):
        c = CPTChannel(name="qc", unit="MPa", values=[1.0, 2.5, 3.2])
        assert c.unit == "MPa"
        assert len(c) == 3
        assert c.min() == 1.0
        assert c.max() == 3.2
        assert c.mean() == pytest.approx((1.0 + 2.5 + 3.2) / 3)

    def test_values_coerced_to_float64(self):
        c = CPTChannel(name="u2", values=[0, 1, 2])
        assert c.values.dtype == np.float64

    def test_accepts_numpy_input(self):
        arr = np.array([1.0, 2.0, 3.0])
        c = CPTChannel(name="fs", values=arr)
        assert len(c) == 3

    def test_rejects_multi_dimensional(self):
        with pytest.raises(ValueError, match="1-D"):
            CPTChannel(name="x", values=np.array([[1, 2], [3, 4]]))

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name"):
            CPTChannel(name="")

    def test_iter(self):
        c = CPTChannel(name="q", values=[1.0, 2.0])
        assert list(c) == [1.0, 2.0]

    def test_stats_on_empty_are_nan(self):
        import math

        c = CPTChannel(name="x")
        assert math.isnan(c.min())
        assert math.isnan(c.max())
        assert math.isnan(c.mean())


# ---------------------------------------------------------------------------
# AcquisitionEvent
# ---------------------------------------------------------------------------


class TestAcquisitionEvent:
    def test_minimal(self):
        e = AcquisitionEvent(timestamp=datetime(2026, 4, 14, 10, 0), event_type="Thrust")
        assert e.event_type == "Thrust"
        assert e.message == ""

    def test_frozen(self):
        e = AcquisitionEvent(timestamp=datetime(2026, 4, 14), event_type="Thrust")
        with pytest.raises(Exception):
            e.message = "changed"  # type: ignore[misc]

    def test_rejects_non_datetime(self):
        with pytest.raises(TypeError):
            AcquisitionEvent(timestamp="2026-04-14", event_type="Thrust")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CPTHeader
# ---------------------------------------------------------------------------


class TestCPTHeader:
    def test_minimal_id_required(self):
        h = CPTHeader(sounding_id="CPT-01")
        assert h.sounding_id == "CPT-01"
        assert h.sounding_type == "UNKNOWN"
        assert h.events == []

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError, match="sounding_id"):
            CPTHeader(sounding_id="")

    def test_area_ratio_range(self):
        CPTHeader(sounding_id="x", cone_area_ratio_a=0.0)
        CPTHeader(sounding_id="x", cone_area_ratio_a=1.0)
        CPTHeader(sounding_id="x", cone_area_ratio_a=0.7032)
        with pytest.raises(ValueError, match="area_ratio"):
            CPTHeader(sounding_id="x", cone_area_ratio_a=1.5)
        with pytest.raises(ValueError, match="area_ratio"):
            CPTHeader(sounding_id="x", cone_area_ratio_a=-0.1)

    def test_negative_base_area_rejected(self):
        with pytest.raises(ValueError, match="base_area"):
            CPTHeader(sounding_id="x", cone_base_area_mm2=-1)

    def test_timing_order(self):
        t0 = datetime(2026, 4, 14, 9)
        t1 = datetime(2026, 4, 14, 10)
        h = CPTHeader(sounding_id="x", started_at=t0, completed_at=t1)
        assert h.duration_s == 3600
        with pytest.raises(ValueError, match="completed_at"):
            CPTHeader(sounding_id="x", started_at=t1, completed_at=t0)

    def test_record_event_appends(self):
        h = CPTHeader(sounding_id="x")
        t0 = datetime(2026, 4, 14, 10)
        h.record_event(t0, "Thrust", "start of push")
        h.record_event(t0 + timedelta(seconds=30), "Seabed Baseline")
        assert len(h.events) == 2
        assert h.events[0].message == "start of push"
        assert h.events[1].event_type == "Seabed Baseline"

    def test_is_marine(self):
        h = CPTHeader(sounding_id="x", water_depth_m=30.5)
        assert h.is_marine is True
        assert CPTHeader(sounding_id="x", water_depth_m=0).is_marine is False
        assert CPTHeader(sounding_id="x").is_marine is False

    def test_has_equipment_info(self):
        assert not CPTHeader(sounding_id="x").has_equipment_info
        assert CPTHeader(
            sounding_id="x", equipment_vendor="Gouda"
        ).has_equipment_info

    def test_jaco_defaults_shape(self):
        h = CPTHeader(
            sounding_id="CPT-01",
            equipment_vendor="Gouda Geo-Equipment",
            equipment_model="WISON-APB",
            cone_base_area_mm2=200.0,
            cone_area_ratio_a=0.7032,
        )
        assert h.cone_base_area_mm2 == 200.0
        assert h.cone_area_ratio_a == pytest.approx(0.7032)


# ---------------------------------------------------------------------------
# CPTSounding A2.1 extensions
# ---------------------------------------------------------------------------


class TestSoundingCanonicalLayer:
    def _base(self) -> CPTSounding:
        return CPTSounding(handle=100, element_tag="100", name="CPT-01")

    def test_a20_fields_default_empty(self):
        s = self._base()
        assert s.header is None
        assert s.channels == {}
        assert s.derived == {}
        assert s.strata == []
        assert s.metadata == {}
        assert s.ags_source is None

    def test_attach_header_and_channels(self):
        s = self._base()
        s.header = CPTHeader(sounding_id="CPT-01")
        s.channels["qc"] = CPTChannel(
            name="qc", unit="MPa", values=[1, 2, 3]
        )
        s.channels["depth"] = CPTChannel(
            name="depth", unit="m", values=[0, 0.5, 1.0, 1.5, 2.0]
        )
        assert s.has_channel("qc")
        assert s.has_channel("depth")
        assert s.get_channel("qc").mean() == 2.0
        assert s.total_depth_m == 2.0

    def test_total_depth_falls_back_to_max_depth(self):
        s = CPTSounding(handle=1, element_tag="1", max_depth_m=27.5)
        assert s.total_depth_m == 27.5

    def test_get_channel_missing_raises(self):
        s = self._base()
        with pytest.raises(KeyError, match="qc"):
            s.get_channel("qc")

    def test_derived_lookup(self):
        s = self._base()
        s.derived["Ic"] = CPTChannel(name="Ic", values=[1.5, 2.0, 2.5])
        assert s.has_channel("Ic")
        assert s.get_channel("Ic").max() == 2.5

    def test_strata_attachment(self):
        s = self._base()
        s.strata.append(StratumLayer(top_m=0, base_m=2.5, description="Sand"))
        s.strata.append(StratumLayer(top_m=2.5, base_m=5.0, description="Clay"))
        assert len(s.strata) == 2
        assert s.strata[0].thickness_m == 2.5

    def test_a20_parser_output_still_valid(self, synth_cpt_bytes=None):
        """A2.0 reader output must continue to work with A2.1 fields empty."""
        from geoview_cpt.parsers.tests.conftest import _build_synth_bytes
        from geoview_cpt.parsers.cpet_it_v30 import read_cpt_v30_bytes

        proj = read_cpt_v30_bytes(_build_synth_bytes())
        for s in proj:
            # A2.0 fields populated
            assert s.name
            assert s.element_tag
            # A2.1 fields empty
            assert s.header is None
            assert s.channels == {}
            assert s.strata == []
