"""Tests for geoview_cpt.parsers.cpt_text_bundle — Phase A-2 A2.2d."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.model import CPTSounding
from geoview_cpt.parsers.cpt_text_bundle import (
    CLOG_EVENT_TYPE_MAP,
    CptBundleParseError,
    parse_cdf_bundle,
    parse_clog_events,
)


# ---------------------------------------------------------------------------
# Synthetic CLog factory
# ---------------------------------------------------------------------------


_SAMPLE_CLOG = """Date/Time,Details
01/09/2025 18:20:11,<
TELEMETRY V4.0 AUTO-TUNING REPORT
---------------------------------
 SUBSEA:  LEVEL=152, QUALITY= 76.
 TOPSIDE: LEVEL=127, QUALITY= 99.
>
COMPLETION CODE: [2]
01/09/2025 18:20:11,Deck Baseline
01/09/2025 18:31:28,Seabed Baseline
01/09/2025 18:31:37,Thrust
01/09/2025 18:34:56,Stop Thrust
01/09/2025 18:34:57,Maximum Push Distance Reached
01/09/2025 18:35:04,Retract
01/09/2025 18:36:49,Cone Up
01/09/2025 18:36:51,Post Baseline
01/09/2025 18:36:58,Terminated Deck to Deck data stores
"""


@pytest.fixture
def synth_clog(tmp_path) -> Path:
    p = tmp_path / "CPT000001.CLog"
    p.write_text(_SAMPLE_CLOG, encoding="utf-8", newline="\r\n")
    return p


# ---------------------------------------------------------------------------
# parse_clog_events
# ---------------------------------------------------------------------------


class TestParseClogEventsSynthetic:
    def test_returns_events(self, synth_clog):
        events = parse_clog_events(synth_clog)
        # Multi-line telemetry block + 9 single-line events
        assert len(events) == 10

    def test_event_types_mapped(self, synth_clog):
        events = parse_clog_events(synth_clog)
        types = [e.event_type for e in events]
        assert "Deck Baseline" in types
        assert "Post Baseline" in types
        assert "Thrust" in types
        assert "Seabed Baseline" in types
        assert "Cone Up" in types

    def test_timestamps_parsed(self, synth_clog):
        events = parse_clog_events(synth_clog)
        assert events[1].timestamp == datetime(2025, 9, 1, 18, 20, 11)
        assert events[-1].timestamp == datetime(2025, 9, 1, 18, 36, 58)

    def test_multiline_block_preserved(self, synth_clog):
        events = parse_clog_events(synth_clog)
        telemetry = events[0]
        assert telemetry.event_type == "Other"
        assert "TELEMETRY" in telemetry.message
        assert "SUBSEA" in telemetry.message

    def test_unknown_label_becomes_other(self, tmp_path):
        p = tmp_path / "x.CLog"
        p.write_text(
            "Date/Time,Details\n01/09/2025 10:00:00,Custom event\n",
            encoding="utf-8",
        )
        events = parse_clog_events(p)
        assert len(events) == 1
        assert events[0].event_type == "Other"
        assert events[0].message == "Custom event"

    def test_event_type_map_coverage(self):
        # Key canonical labels must be present
        for k in ("Thrust", "Deck Baseline", "Retract", "Cone Up"):
            assert k in CLOG_EVENT_TYPE_MAP


class TestParseClogErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(CptBundleParseError, match="not found"):
            parse_clog_events(tmp_path / "nope.CLog")


# ---------------------------------------------------------------------------
# Synthetic .cdf bundle
# ---------------------------------------------------------------------------


_SAMPLE_CDF = '''"Software Version"
"6.98:1"

"Project Name","Client Name","Location","Vessel","Client","Operator","Cone","Notes"
"JAko","geo","offshore","geoview DP01","-","Park","0492",""

"Fix Number","Water Depth","Push Name","Test Number","Raw Data File","Computed Data File","Max Tip (MPa)","Max Incline (Degrees)","Max Push (m)"
"1","88","CPT01","0001","CPT010001.rdf","CPT010001.cdf","34.32","30","4"

"Tip Area (mm)","N Value"
"200.00","15"

"Tip Area Factor",0.7032
"Hydrostatic Pressure (MPa)",0.87

"Date&Time","Pen (m)","Tip (MPa Qc)","Cu (MPa)","Sleeve (MPa)","Measured Pore (MPa)","TiltX (Degrees)","TiltY (Degrees)","Combined Tilt (Degrees)","Altimeter (m)","Voltage (V)","Current (A)"
#01/09/2025 18:31:39#,0.001,0.002,0.000,0.000,0.000,0,0,0,00.00,230,1.44
#01/09/2025 18:31:40#,0.010,0.005,0.000,0.000,0.001,0,0,0,00.00,230,1.44
#01/09/2025 18:31:41#,0.025,0.012,0.000,0.001,0.002,0,0,0,00.00,230,1.44
#01/09/2025 18:31:42#,0.050,0.021,0.000,0.002,0.005,0,0,0,00.00,230,1.44
#01/09/2025 18:31:43#,0.100,0.045,0.000,0.003,0.010,0,0,0,00.00,230,1.44
'''


@pytest.fixture
def synth_cdf(tmp_path) -> Path:
    p = tmp_path / "CPT010001.cdf"
    p.write_text(_SAMPLE_CDF, encoding="utf-8")
    return p


class TestParseCdfBundleSynthetic:
    def test_returns_sounding(self, synth_cdf):
        s = parse_cdf_bundle(synth_cdf)
        assert isinstance(s, CPTSounding)
        assert s.header is not None

    def test_header_fields(self, synth_cdf):
        s = parse_cdf_bundle(synth_cdf)
        assert s.header.project_name == "JAko"
        assert s.header.vessel == "geoview DP01"
        assert s.header.operator == "Park"
        assert s.header.water_depth_m == 88.0
        assert s.header.cone_base_area_mm2 == 200.0
        assert abs(s.header.cone_area_ratio_a - 0.7032) < 1e-6
        assert s.header.sounding_id == "CPT01"

    def test_channels_populated_canonical_units(self, synth_cdf):
        s = parse_cdf_bundle(synth_cdf)
        assert s.channels["depth"].unit == "m"
        assert s.channels["qc"].unit == "MPa"
        assert s.channels["fs"].unit == "kPa"
        assert s.channels["u2"].unit == "kPa"
        # fs converted: raw 0.001 MPa → 1 kPa
        assert s.channels["fs"].values[2] == pytest.approx(1.0, abs=1e-6)

    def test_first_timestamp(self, synth_cdf):
        s = parse_cdf_bundle(synth_cdf)
        assert s.header.started_at is not None
        assert s.header.started_at.year == 2025

    def test_sibling_clog_attached(self, tmp_path):
        cdf = tmp_path / "CPT010001.cdf"
        cdf.write_text(_SAMPLE_CDF, encoding="utf-8")
        clog = tmp_path / "CPT010001.CLog"
        clog.write_text(_SAMPLE_CLOG, encoding="utf-8")
        s = parse_cdf_bundle(cdf)
        assert len(s.header.events) > 0

    def test_explicit_clog_override(self, tmp_path):
        cdf = tmp_path / "CPT010001.cdf"
        cdf.write_text(_SAMPLE_CDF, encoding="utf-8")
        clog = tmp_path / "other_log.CLog"
        clog.write_text(_SAMPLE_CLOG, encoding="utf-8")
        s = parse_cdf_bundle(cdf, clog_path=clog)
        assert len(s.header.events) > 0


class TestParseCdfErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(CptBundleParseError, match="not found"):
            parse_cdf_bundle(tmp_path / "nope.cdf")

    def test_no_data_header(self, tmp_path):
        p = tmp_path / "bad.cdf"
        p.write_text('"Software Version"\n"6.98:1"\n', encoding="utf-8")
        with pytest.raises(CptBundleParseError, match="Date&Time"):
            parse_cdf_bundle(p)


# ---------------------------------------------------------------------------
# Real JAKO CPT01 bundle (optional)
# ---------------------------------------------------------------------------


_REAL_CDF = Path(
    r"H:/자코/JAKO_Korea_area/Raw_data/Jako_Korea_area_CPT_raw_data/CPT01/CPT010001.cdf"
)
_REAL_CLOG = Path(
    r"H:/자코/JAKO_Korea_area/Raw_data/Jako_Korea_area_CPT_raw_data/CPT01/CPT010001.CLog"
)

jako_required = pytest.mark.skipif(
    not (_REAL_CDF.exists() and _REAL_CLOG.exists()),
    reason="JAKO CPT01 vendor bundle not mounted",
)


@pytest.fixture(scope="session")
def real_jako_bundle():
    if not (_REAL_CDF.exists() and _REAL_CLOG.exists()):
        pytest.skip("JAKO CPT01 vendor bundle not mounted")
    return parse_cdf_bundle(_REAL_CDF)


@jako_required
class TestRealJakoBundle:
    def test_reads_cpt01(self, real_jako_bundle):
        s = real_jako_bundle
        assert s.header.project_name.lower().startswith("jako")
        assert len(s.channels["depth"]) > 100

    def test_events_from_clog(self, real_jako_bundle):
        s = real_jako_bundle
        event_types = {e.event_type for e in s.header.events}
        assert "Deck Baseline" in event_types
        assert "Post Baseline" in event_types
        assert "Thrust" in event_types

    def test_header_equipment_defaults(self, real_jako_bundle):
        s = real_jako_bundle
        assert s.header.equipment_vendor == "Gouda Geo-Equipment"
        assert s.header.equipment_model == "WISON-APB"
