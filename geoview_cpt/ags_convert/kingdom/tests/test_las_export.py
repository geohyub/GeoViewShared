"""
Tests for the Kingdom LAS exporter — Phase A-4 Week 17 A4.1.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.ags_convert.kingdom import (
    DEFAULT_CURVES,
    build_kingdom_las,
)
from geoview_cpt.ags_convert.wrapper import AgsConvertError
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding


def _has_lasio() -> bool:
    try:
        import lasio  # noqa: F401

        return True
    except ImportError:
        return False


HAS_LASIO = _has_lasio()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sounding(*, with_derived: bool = True) -> CPTSounding:
    d = np.linspace(0.5, 5.0, 10)
    s = CPTSounding(handle=1, element_tag="", name="CPT01", max_depth_m=5.0)
    s.header = CPTHeader(
        sounding_id="CPT01",
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.8,
        loca_x=123.45,
        loca_y=456.78,
        loca_crs="EPSG:5179",
        water_depth_m=18.5,
        started_at=datetime(2025, 10, 1, 9, 0, 0),
    )
    s.channels = {
        "depth": CPTChannel("depth", "m", d),
        "qc":    CPTChannel("qc", "MPa", np.linspace(1.0, 5.0, 10)),
        "fs":    CPTChannel("fs", "kPa", np.linspace(10.0, 50.0, 10)),
        "u2":    CPTChannel("u2", "kPa", np.linspace(0.0, 20.0, 10)),
    }
    if with_derived:
        s.derived = {
            "qt": CPTChannel("qt", "MPa", np.linspace(1.05, 5.05, 10)),
            "Ic": CPTChannel("Ic", "", np.linspace(1.5, 3.0, 10)),
        }
    else:
        s.derived = {}
    return s


# ---------------------------------------------------------------------------
# Module-level invariants (always-on)
# ---------------------------------------------------------------------------


def test_default_curves_starts_with_dept():
    assert DEFAULT_CURVES[0][0] == "DEPT"


def test_default_curves_includes_qt_fs_u2_ic():
    mnemonics = {c[0] for c in DEFAULT_CURVES}
    assert {"DEPT", "QT", "FS", "U2", "IC"} <= mnemonics


# ---------------------------------------------------------------------------
# Error paths (work without lasio installed)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(HAS_LASIO, reason="error path only fires without lasio")
def test_build_las_without_lasio_raises(tmp_path):
    s = _make_sounding()
    with pytest.raises(AgsConvertError, match="lasio"):
        build_kingdom_las(s, tmp_path / "x.las")


def test_build_las_no_dept_curve_raises(tmp_path):
    if not HAS_LASIO:
        pytest.skip("requires lasio for downstream validation")
    s = _make_sounding()
    with pytest.raises(AgsConvertError, match="DEPT"):
        build_kingdom_las(s, tmp_path / "x.las", curves=[("QT", "derived", "qt", "MPa", "qt")])


def test_build_las_missing_depth_channel_raises(tmp_path):
    if not HAS_LASIO:
        pytest.skip("requires lasio")
    s = _make_sounding()
    s.channels.pop("depth")
    with pytest.raises(AgsConvertError, match="depth"):
        build_kingdom_las(s, tmp_path / "x.las")


# ---------------------------------------------------------------------------
# Happy path (require lasio)
# ---------------------------------------------------------------------------


pytestmark_lasio = pytest.mark.skipif(not HAS_LASIO, reason="lasio not installed")


@pytestmark_lasio
def test_build_las_creates_file(tmp_path):
    s = _make_sounding()
    out = tmp_path / "CPT01.las"
    build_kingdom_las(s, out, project_client="Geoview")
    assert out.exists()
    assert out.stat().st_size > 200


@pytestmark_lasio
def test_build_las_creates_parent_dirs(tmp_path):
    s = _make_sounding()
    out = tmp_path / "a" / "b" / "CPT01.las"
    build_kingdom_las(s, out)
    assert out.exists()


@pytestmark_lasio
def test_build_las_well_section_populated(tmp_path):
    import lasio

    s = _make_sounding()
    out = tmp_path / "CPT01.las"
    build_kingdom_las(s, out, project_client="Geoview")
    las = lasio.read(str(out))
    assert las.well.WELL.value == "CPT01"
    assert "EPSG:5179" in str(las.well.LOC.value)
    assert float(las.well.STRT.value) == pytest.approx(0.5)
    assert float(las.well.STOP.value) == pytest.approx(5.0)
    assert str(las.well.DATE.value) == "2025-10-01"
    assert "Geoview" in str(las.well.COMP.value)


@pytestmark_lasio
def test_build_las_curves_in_default_order(tmp_path):
    import lasio

    s = _make_sounding()
    out = tmp_path / "CPT01.las"
    build_kingdom_las(s, out)
    las = lasio.read(str(out))
    mnemonics = [c.mnemonic for c in las.curves]
    assert mnemonics[0] == "DEPT"
    assert "QT" in mnemonics
    assert "FS" in mnemonics
    assert "U2" in mnemonics
    assert "IC" in mnemonics
    # SBT not populated → must be skipped (no SBT channel in fixture)
    assert "SBT" not in mnemonics


@pytestmark_lasio
def test_build_las_skips_missing_derived_curves(tmp_path):
    import lasio

    s = _make_sounding(with_derived=False)
    out = tmp_path / "CPT01.las"
    build_kingdom_las(s, out)
    las = lasio.read(str(out))
    mnemonics = [c.mnemonic for c in las.curves]
    assert "DEPT" in mnemonics
    assert "FS" in mnemonics
    assert "U2" in mnemonics
    # qt / Ic not in derived → skipped
    assert "QT" not in mnemonics
    assert "IC" not in mnemonics


@pytestmark_lasio
def test_build_las_curve_data_round_trip(tmp_path):
    import lasio

    s = _make_sounding()
    out = tmp_path / "CPT01.las"
    build_kingdom_las(s, out)
    las = lasio.read(str(out))
    np.testing.assert_allclose(
        las["DEPT"], s.channels["depth"].values, rtol=1e-6
    )
    np.testing.assert_allclose(
        las["FS"], s.channels["fs"].values, rtol=1e-6
    )
    np.testing.assert_allclose(
        las["QT"], s.derived["qt"].values, rtol=1e-4
    )


@pytestmark_lasio
def test_build_las_custom_curve_list(tmp_path):
    import lasio

    s = _make_sounding()
    out = tmp_path / "CPT01.las"
    custom = [
        ("DEPT", "depth",   "depth", "m", "Depth"),
        ("QT",   "derived", "qt",    "MPa", "qt"),
    ]
    build_kingdom_las(s, out, curves=custom)
    las = lasio.read(str(out))
    assert [c.mnemonic for c in las.curves] == ["DEPT", "QT"]


@pytestmark_lasio
def test_build_las_handles_mismatched_curve_length(tmp_path):
    import lasio

    s = _make_sounding()
    # Truncate qt to half — exporter must pad with NULL, not crash
    s.derived["qt"] = CPTChannel(
        "qt", "MPa", np.linspace(1.0, 3.0, 5)
    )
    out = tmp_path / "CPT01.las"
    build_kingdom_las(s, out)
    las = lasio.read(str(out))
    assert "QT" in [c.mnemonic for c in las.curves]
    qt = las["QT"]
    assert len(qt) == 10
    # Last 5 samples must be NULL (-999.25 or NaN after lasio parse)
    assert np.isnan(qt[-1]) or qt[-1] == -999.25
