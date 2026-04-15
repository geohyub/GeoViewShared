"""Tests for geoview_cpt.parsers.gef — Phase A-2 A2.3."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.model import CPTSounding
from geoview_cpt.parsers.gef import GefParseError, parse_gef


# ---------------------------------------------------------------------------
# Synthetic GEF factory
# ---------------------------------------------------------------------------


_SAMPLE_GEF = """#GEFID= 1, 1, 0
#COLUMN= 4
#COLUMNINFO= 1, m, gecorrigeerde sondeerlengte, 1
#COLUMNINFO= 2, MPa, conusweerstand, 2
#COLUMNINFO= 3, MPa, wrijvingsweerstand, 3
#COLUMNINFO= 4, MPa, waterspanning u2, 6
#COLUMNVOID= 1, -9999
#COLUMNVOID= 2, -9999
#COLUMNVOID= 3, -9999
#COLUMNVOID= 4, -9999
#COMPANYID= Geoview B.V., , 0
#LOCATION= Amsterdam Test Site
#PROJECTNAME= Test Project
#MEASUREMENTTEXT= 1, BH-01
#EOH=
  0.020  0.050  0.0010  0.0005
  0.040  0.060  0.0012  0.0008
  0.060  0.075  0.0015  0.0010
  0.080  0.080  0.0018  0.0012
  0.100  0.090  0.0020  0.0015
  0.120  0.110  0.0025  0.0018
  0.140  0.130  0.0030  0.0020
  0.160  0.160  0.0035  0.0025
  0.180  0.200  0.0040  0.0030
  0.200  0.250  0.0050  0.0035
"""


@pytest.fixture
def synth_gef(tmp_path) -> Path:
    p = tmp_path / "synth.gef"
    p.write_text(_SAMPLE_GEF, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestParseGef:
    def test_returns_sounding(self, synth_gef):
        s = parse_gef(synth_gef)
        assert isinstance(s, CPTSounding)

    def test_header_fields(self, synth_gef):
        s = parse_gef(synth_gef)
        assert s.header.project_name == "Test Project"
        assert s.header.sounding_id == "BH-01"

    def test_channels_populated(self, synth_gef):
        s = parse_gef(synth_gef)
        assert set(s.channels.keys()) == {"depth", "qc", "fs", "u2"}

    def test_depth_range(self, synth_gef):
        s = parse_gef(synth_gef)
        assert s.channels["depth"].values[0] == pytest.approx(0.020)
        assert s.channels["depth"].values[-1] == pytest.approx(0.200)

    def test_fs_converted_to_kpa(self, synth_gef):
        s = parse_gef(synth_gef)
        # First row: 0.0010 MPa → 1.0 kPa
        assert s.channels["fs"].unit == "kPa"
        assert s.channels["fs"].values[0] == pytest.approx(1.0)

    def test_u2_converted_to_kpa(self, synth_gef):
        s = parse_gef(synth_gef)
        assert s.channels["u2"].unit == "kPa"
        assert s.channels["u2"].values[0] == pytest.approx(0.5)

    def test_metadata_captured(self, synth_gef):
        s = parse_gef(synth_gef)
        meta = s.metadata
        assert meta["source_format"] == "gef"
        assert meta["company"] == "Geoview B.V., , 0"
        assert meta["location"] == "Amsterdam Test Site"


# ---------------------------------------------------------------------------
# Void sentinel handling
# ---------------------------------------------------------------------------


class TestVoidSentinel:
    def test_void_becomes_nan(self, tmp_path):
        gef = """#COLUMN= 2
#COLUMNINFO= 1, m, depth, 1
#COLUMNINFO= 2, MPa, qc, 2
#COLUMNVOID= 2, -9999
#EOH=
 0.02 0.10
 0.04 -9999
 0.06 0.15
"""
        p = tmp_path / "void.gef"
        p.write_text(gef)
        s = parse_gef(p)
        qc = s.channels["qc"].values
        assert np.isnan(qc[1])
        assert qc[0] == pytest.approx(0.10)
        assert qc[2] == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# Tip-only sounding
# ---------------------------------------------------------------------------


class TestTipOnly:
    def test_no_fs_u2(self, tmp_path):
        gef = """#COLUMN= 2
#COLUMNINFO= 1, m, depth, 1
#COLUMNINFO= 2, MPa, qc, 2
#EOH=
 0.02 0.10
 0.04 0.12
 0.06 0.15
"""
        p = tmp_path / "tip_only.gef"
        p.write_text(gef)
        s = parse_gef(p)
        assert "qc" in s.channels
        assert "fs" not in s.channels
        assert "u2" not in s.channels


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(GefParseError, match="not found"):
            parse_gef(tmp_path / "nope.gef")

    def test_no_eoh(self, tmp_path):
        p = tmp_path / "bad.gef"
        p.write_text("#COLUMN= 1\n#COLUMNINFO= 1, m, depth, 1\n")
        with pytest.raises(GefParseError, match="EOH"):
            parse_gef(p)

    def test_no_column_info(self, tmp_path):
        p = tmp_path / "bad.gef"
        p.write_text("#COLUMN= 0\n#EOH=\n 0.02 0.10\n")
        with pytest.raises(GefParseError, match="COLUMNINFO"):
            parse_gef(p)

    def test_no_data_rows(self, tmp_path):
        p = tmp_path / "bad.gef"
        p.write_text("#COLUMNINFO= 1, m, depth, 1\n#EOH=\n")
        with pytest.raises(GefParseError, match="no data"):
            parse_gef(p)
