"""Tests for geoview_cpt.parsers.excel_jako — Phase A-2 A2.2b."""
from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from geoview_cpt.model import CPTSounding
from geoview_cpt.parsers.excel_jako import (
    JakoParseError,
    JakoParseOptions,
    detect_jako_xls,
    parse_jako_xls,
)


# ---------------------------------------------------------------------------
# Synthetic JAKO .xls factory — uses xlwt so we can emit a true BIFF8 file
# that xlrd will read the same way it reads the vendor export.
# ---------------------------------------------------------------------------


def _make_jako_xls(
    tmp_path: Path,
    *,
    rows: int = 10,
    push_name: str = "CPT01",
    tip_area_mm2: float = 200.0,
    tip_area_factor: float = 0.7032,
    missing_data_header: bool = False,
) -> Path:
    """
    Synthesize a JAKO-shaped workbook. We emit ``.xlsx`` via openpyxl —
    :func:`parse_jako_xls` dispatches on extension, so the same reader
    handles both the real vendor ``.xls`` and our synthetic copy.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CPT010001"

    # Helper uses 1-based indices (openpyxl convention)
    def w(r, c, v):
        ws.cell(r + 1, c + 1, v)

    # r0/r1 software version
    w(0, 0, "Software Version")
    w(1, 0, "6.98:1")

    # r3 labels / r4 values
    labels3 = [
        "Project Name", "Client Name", "Location", "Vessel",
        "Client", "Operator", "Cone", "Notes",
    ]
    values4 = ["JAko", "geo", "offshore", "geoview DP01", "-", "Park", 492.0, ""]
    for c, (lbl, val) in enumerate(zip(labels3, values4)):
        w(3, c, lbl)
        w(4, c, val)

    # r6 labels / r7 values
    labels6 = [
        "Fix Number", "Water Depth", "Push Name", "Test Number",
        "Raw Data File", "Computed Data File", "Max Tip (MPa)", "Max Incline (Degrees)",
    ]
    values7 = [1.0, 88.0, push_name, 1.0, "CPT010001.rdf", "CPT010001.cdf", "34.32", "30"]
    for c, (lbl, val) in enumerate(zip(labels6, values7)):
        w(6, c, lbl)
        w(7, c, val)

    # r9 labels / r10 values
    w(9, 0, "Tip Area (mm)")
    w(9, 1, "N Value")
    w(10, 0, tip_area_mm2)
    w(10, 1, 15.0)

    # r12/r13 free text
    w(12, 0, f"Tip Area Factor = {tip_area_factor}")
    w(13, 0, "Hydrostatic Pressure (MPa) = 0.87")

    # r15 data header
    if missing_data_header:
        w(15, 0, "Bogus")
    else:
        data_header = [
            "Date&Time", "Pen (m)", "Tip (MPa Qc)", "Cu (MPa)",
            "Sleeve (MPa)", "Measured Pore (MPa)",
            "TiltX (Degrees)", "TiltY (Degrees)", "Combined Tilt (Degrees)",
            "Altimeter (m)", "Voltage (V)", "Current (A)",
        ]
        for c, lbl in enumerate(data_header):
            w(15, c, lbl)

    for i in range(rows):
        r = 16 + i
        depth = 0.001 + i * 0.002
        qc = 0.002 + i * 0.01
        fs = 0.0005 + i * 0.001
        u2 = 0.001 + i * 0.0005
        incl = 0.1 * (i % 5)
        w(r, 0, "#01/09/2025 18:31:39#")
        w(r, 1, depth)
        w(r, 2, qc)
        w(r, 3, 0.0)
        w(r, 4, fs)
        w(r, 5, u2)
        w(r, 6, 0.0)
        w(r, 7, 0.0)
        w(r, 8, incl)
        w(r, 9, 0.0)
        w(r, 10, 230.0)
        w(r, 11, 1.44)

    out = tmp_path / "synth_jako.xlsx"
    wb.save(out)
    wb.close()
    return out


@pytest.fixture
def synth_jako_path(tmp_path) -> Path:
    return _make_jako_xls(tmp_path)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestParseJakoSynthetic:
    def test_returns_cpt_sounding(self, synth_jako_path):
        s = parse_jako_xls(synth_jako_path)
        assert isinstance(s, CPTSounding)

    def test_metadata_header_fields(self, synth_jako_path):
        s = parse_jako_xls(synth_jako_path)
        assert s.header is not None
        assert s.header.project_name == "JAko"
        assert s.header.vessel == "geoview DP01"
        assert s.header.operator == "Park"
        assert s.header.water_depth_m == 88.0

    def test_cone_geometry_from_file(self, synth_jako_path):
        s = parse_jako_xls(synth_jako_path)
        assert s.header.cone_base_area_mm2 == 200.0
        assert s.header.cone_area_ratio_a == pytest.approx(0.7032)

    def test_equipment_defaults(self, synth_jako_path):
        s = parse_jako_xls(synth_jako_path)
        assert s.header.equipment_vendor == "Gouda Geo-Equipment"
        assert s.header.equipment_model == "WISON-APB"

    def test_channels_populated(self, synth_jako_path):
        s = parse_jako_xls(synth_jako_path)
        assert set(s.channels.keys()) == {"depth", "qc", "fs", "u2", "incl"}
        assert len(s.channels["depth"]) == 10

    def test_fs_u2_converted_to_kpa(self, synth_jako_path):
        s = parse_jako_xls(synth_jako_path)
        # first row fs = 0.0005 MPa → 0.5 kPa
        assert s.channels["fs"].unit == "kPa"
        assert s.channels["fs"].values[0] == pytest.approx(0.5)
        assert s.channels["u2"].unit == "kPa"

    def test_sounding_id_from_push_name(self, synth_jako_path):
        s = parse_jako_xls(synth_jako_path)
        assert s.name == "CPT01"

    def test_timestamps_extracted(self, synth_jako_path):
        s = parse_jako_xls(synth_jako_path)
        assert s.header.started_at is not None
        assert s.header.completed_at is not None
        assert s.header.started_at.year == 2025

    def test_metadata_captured(self, synth_jako_path):
        s = parse_jako_xls(synth_jako_path)
        meta = s.metadata
        assert meta["source_format"] == "jako_xls"
        assert meta["software_version"] == "6.98:1"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(JakoParseError, match="not found"):
            parse_jako_xls(tmp_path / "nope.xls")

    def test_missing_data_header(self, tmp_path):
        path = _make_jako_xls(tmp_path, missing_data_header=True)
        with pytest.raises(JakoParseError, match="data header"):
            parse_jako_xls(path)


# ---------------------------------------------------------------------------
# Detect
# ---------------------------------------------------------------------------


class TestDetect:
    def test_positive(self, synth_jako_path):
        assert detect_jako_xls(synth_jako_path) is True

    def test_missing_file(self, tmp_path):
        assert detect_jako_xls(tmp_path / "nope.xls") is False

    def test_wrong_extension(self, tmp_path):
        p = tmp_path / "x.txt"
        p.write_text("hi")
        assert detect_jako_xls(p) is False


# ---------------------------------------------------------------------------
# Real JAKO .xls file (optional)
# ---------------------------------------------------------------------------


_REAL_JAKO = Path(r"H:/자코/JAKO_Korea_area/Excel_변환_data/CPT01.xls")
jako_required = pytest.mark.skipif(
    not _REAL_JAKO.exists(),
    reason="JAKO real sample not mounted (H: drive)",
)


@pytest.fixture(scope="session")
def real_jako_sounding():
    if not _REAL_JAKO.exists():
        pytest.skip("JAKO real sample not mounted")
    return parse_jako_xls(_REAL_JAKO)


@jako_required
class TestRealJako:
    def test_reads_cpt01(self, real_jako_sounding):
        s = real_jako_sounding
        assert s.header is not None
        assert s.header.project_name.lower().startswith("jako")
        assert s.header.cone_base_area_mm2 == 200.0
        assert s.header.cone_area_ratio_a == pytest.approx(0.7032)

    def test_data_count(self, real_jako_sounding):
        s = real_jako_sounding
        assert len(s.channels["depth"]) > 100
        # Real CPT01 has ~3943 samples
        assert len(s.channels["qc"]) == len(s.channels["depth"])

    def test_header_timestamps(self, real_jako_sounding):
        s = real_jako_sounding
        assert s.header.started_at is not None
        assert s.header.started_at.year == 2025
