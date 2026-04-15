"""
Byte-level round-trip smoke tests — Week 14 A3.2 Part 2.

**Definition.** Byte-level round-trip = *dump idempotency after the
first load*:

    write_ags(sounding) → file_v1
    load_ags(file_v1)   → bundle_v1
    dump_ags(bundle_v1) → file_v2
    load_ags(file_v2)   → bundle_v2
    dump_ags(bundle_v2) → file_v3
    assert file_v2.bytes == file_v3.bytes

The first write→load cycle is explicitly excluded because
**python-ags4 mangles ``TRAN_DLIM = "`` on reload** (the embedded
quote is dropped, not preserved). See
``docs/python_ags4_gaps.md`` — this is logged as Gap #1 and
prevents `v1 == v2`. Once the bundle has passed through the library
once, however, subsequent load→dump cycles are idempotent, which is
the property downstream consumers actually rely on.

Week 14 shipped samples 1-2; Week 15 closes out 3-5:

    1. JAKO-style synthetic CPT (SCPG/SCPT)
    2. HELMS YW-01 real pcpt
    3. Golden synthetic CPT with stratigraphy (SCPG/SCPT/SCPP/GEOL)
    4. JAKO-like borehole GI bundle (LOCA/GEOL/SAMP/ISPT)
    5. HELMS-style multi-layer GI fixture (LOCA/GEOL/ISPT)

All five use the same two-pass idempotency pattern and exercise
different code paths in the writer (CPT-only, CPT+strata, GI).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.ags_convert import (
    ProjectMeta,
    dump_ags,
    load_ags,
    write_ags,
)
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding


def _jako_style_sounding() -> CPTSounding:
    d = np.linspace(0.5, 8.0, 20)
    s = CPTSounding(handle=1, element_tag="", name="CPT01", max_depth_m=8.0)
    s.header = CPTHeader(
        sounding_id="CPT01",
        project_name="JAKO",
        client="Geoview",
        equipment_model="Gouda WISON",
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.8,
        loca_x=123456.78,
        loca_y=345678.90,
    )
    s.channels = {
        "depth": CPTChannel("depth", "m", d),
        "qc":    CPTChannel("qc", "MPa", np.linspace(1.0, 6.0, 20)),
        "fs":    CPTChannel("fs", "kPa", np.linspace(10.0, 60.0, 20)),
        "u2":    CPTChannel("u2", "kPa", np.linspace(0.0, 25.0, 20)),
    }
    s.derived = {}
    return s


def _roundtrip_bytes(path_v1, tmp_path, stem: str) -> tuple[bytes, bytes]:
    """Run the two-pass idempotency cycle and return (v2, v3) bytes."""
    bundle_v1 = load_ags(path_v1)
    path_v2 = tmp_path / f"{stem}_v2.ags"
    dump_ags(bundle_v1, path_v2)

    bundle_v2 = load_ags(path_v2)
    path_v3 = tmp_path / f"{stem}_v3.ags"
    dump_ags(bundle_v2, path_v3)
    return path_v2.read_bytes(), path_v3.read_bytes()


def test_byte_roundtrip_jako_synthetic(tmp_path):
    s = _jako_style_sounding()
    meta = ProjectMeta(project_id="P01", client="Geoview")

    path_v1 = tmp_path / "v1.ags"
    write_ags(s, path_v1, project_meta=meta)

    v2_bytes, v3_bytes = _roundtrip_bytes(path_v1, tmp_path, "jako")
    assert v2_bytes == v3_bytes, (
        "JAKO synthetic sample: dump→load→dump must be byte-idempotent"
    )


def test_byte_roundtrip_core_fields_preserved(tmp_path):
    """v1 and v2 may differ in TRAN_DLIM only (python-ags4 gap #1)."""
    s = _jako_style_sounding()
    meta = ProjectMeta(project_id="P01", client="Geoview")

    path_v1 = tmp_path / "v1.ags"
    write_ags(s, path_v1, project_meta=meta)
    bundle_v1 = load_ags(path_v1)
    path_v2 = tmp_path / "v2.ags"
    dump_ags(bundle_v1, path_v2)

    # Semantic check: every SCPT data row byte-identical after round-trip.
    b1 = path_v1.read_bytes()
    b2 = path_v2.read_bytes()
    # Extract SCPT blocks from each
    def _scpt_block(raw: bytes) -> bytes:
        marker = b'"GROUP","SCPT"'
        idx = raw.find(marker)
        assert idx != -1, "SCPT group missing from round-trip"
        return raw[idx:]
    assert _scpt_block(b1) == _scpt_block(b2), (
        "SCPT GROUP bytes must survive the first load→dump unchanged"
    )


def _yw01_path() -> Path | None:
    base = Path(
        "H:/야월해상풍력단지 지반조사 용역 결과보고서_rev7/CPT 데이터 분석/Raw_Data"
    )
    if not base.exists():
        return None
    for p in base.glob("YW-01*.xlsx"):
        return p
    return None


@pytest.mark.skipif(
    _yw01_path() is None, reason="HELMS YW-01 fixture not available"
)
def test_byte_roundtrip_helms_yw01(tmp_path):
    from geoview_cpt.parsers import parse_yw_xlsx

    src = _yw01_path()
    assert src is not None
    result = parse_yw_xlsx(src)
    sounding = result if isinstance(result, CPTSounding) else result.soundings[0]
    meta = ProjectMeta(project_id="HELMS", client="Geoview")

    path_v1 = tmp_path / "yw01_v1.ags"
    write_ags(sounding, path_v1, project_meta=meta)

    v2_bytes, v3_bytes = _roundtrip_bytes(path_v1, tmp_path, "yw01")
    assert v2_bytes == v3_bytes, (
        "HELMS YW-01: dump→load→dump must be byte-idempotent"
    )


# ---------------------------------------------------------------------------
# Sample 3 — Golden synthetic CPT with stratigraphy (exercises GEOL + SCPP)
# ---------------------------------------------------------------------------


def test_byte_roundtrip_golden_synthetic_with_strata(tmp_path):
    from geoview_cpt.model import CPTChannel as _Ch
    from geoview_gi.minimal_model import StratumLayer

    s = _jako_style_sounding()
    s.derived["Ic"] = _Ch("Ic", "", np.linspace(1.5, 3.0, 20))
    s.strata = [
        StratumLayer(top_m=0.0, base_m=3.0, description="sand", legend_code="SP"),
        StratumLayer(top_m=3.0, base_m=6.0, description="silty clay", legend_code="ML"),
        StratumLayer(top_m=6.0, base_m=8.0, description="clay", legend_code="CL"),
    ]
    meta = ProjectMeta(project_id="G01", client="Geoview")
    path_v1 = tmp_path / "golden_v1.ags"
    write_ags(s, path_v1, project_meta=meta)

    # Pin: the golden fixture must emit GEOL + SCPP
    bundle_v1 = load_ags(path_v1)
    assert "GEOL" in bundle_v1.tables
    assert "SCPP" in bundle_v1.tables

    v2_bytes, v3_bytes = _roundtrip_bytes(path_v1, tmp_path, "golden")
    assert v2_bytes == v3_bytes, (
        "Golden synthetic w/ GEOL+SCPP must be byte-idempotent"
    )


# ---------------------------------------------------------------------------
# Sample 4 — JAKO-like GI borehole (LOCA/GEOL/SAMP/ISPT via write_gi_ags)
# ---------------------------------------------------------------------------


def test_byte_roundtrip_gi_borehole_full(tmp_path):
    from datetime import date as _date

    from geoview_cpt.ags_convert import write_gi_ags
    from geoview_gi.minimal_model import (
        Borehole,
        LabSample,
        SPTTest,
        StratumLayer,
    )

    bh = Borehole(
        loca_id="BH-01",
        client="Geoview",
        easting_m=500000.00,
        northing_m=4000000.00,
        crs="EPSG:32652",
        ground_level_m=3.20,
        final_depth_m=15.00,
        start_date=_date(2025, 10, 1),
        end_date=_date(2025, 10, 4),
        method="Rotary Core",
    )
    bh.add_stratum(StratumLayer(top_m=0.0, base_m=2.5, description="fill", legend_code="FL"))
    bh.add_stratum(StratumLayer(top_m=2.5, base_m=8.0, description="sand", legend_code="SP"))
    bh.add_stratum(StratumLayer(top_m=8.0, base_m=15.0, description="clay", legend_code="CL"))
    bh.add_spt(SPTTest(top_m=3.0, seat_blows=5, main_blows=15, n_value=15, method="SPT"))
    bh.add_spt(SPTTest(top_m=6.0, seat_blows=10, main_blows=25, n_value=25, method="SPT"))
    bh.add_spt(SPTTest(top_m=10.0, seat_blows=15, main_blows=40, n_value=40, method="SPT(C)", refusal=True))
    bh.add_sample(LabSample(loca_id="BH-01", sample_id="S-01", sample_type="UT", top_m=4.0, base_m=4.5, recovery_pct=92.0))
    bh.add_sample(LabSample(loca_id="BH-01", sample_id="S-02", sample_type="BT", top_m=9.0, base_m=9.5))

    path_v1 = tmp_path / "gi_full_v1.ags"
    write_gi_ags(bh, path_v1, project_meta=ProjectMeta(project_id="J01"))

    bundle_v1 = load_ags(path_v1)
    for required in ("GEOL", "SAMP", "ISPT"):
        assert required in bundle_v1.tables, f"{required} missing from full GI bundle"

    v2_bytes, v3_bytes = _roundtrip_bytes(path_v1, tmp_path, "gi_full")
    assert v2_bytes == v3_bytes, "Full GI borehole must be byte-idempotent"


# ---------------------------------------------------------------------------
# Sample 5 — HELMS-style minimal GI (LOCA + GEOL only, no samples/SPT)
# ---------------------------------------------------------------------------


def test_byte_roundtrip_gi_minimal_loca_geol(tmp_path):
    from geoview_cpt.ags_convert import write_gi_ags
    from geoview_gi.minimal_model import Borehole, StratumLayer

    bh = Borehole(
        loca_id="BH-HELMS",
        easting_m=200000.00,
        northing_m=3500000.00,
        crs="EPSG:5186",
        final_depth_m=20.0,
        method="Marine rotary",
    )
    for top, base, desc, code in [
        (0.0, 1.5, "seabed mud", "ML"),
        (1.5, 6.0, "silty sand", "SM"),
        (6.0, 12.0, "dense sand", "SP"),
        (12.0, 20.0, "stiff clay", "CL"),
    ]:
        bh.add_stratum(StratumLayer(top_m=top, base_m=base, description=desc, legend_code=code))

    path_v1 = tmp_path / "gi_min_v1.ags"
    write_gi_ags(bh, path_v1)

    bundle_v1 = load_ags(path_v1)
    assert "GEOL" in bundle_v1.tables
    assert "SAMP" not in bundle_v1.tables
    assert "ISPT" not in bundle_v1.tables

    v2_bytes, v3_bytes = _roundtrip_bytes(path_v1, tmp_path, "gi_min")
    assert v2_bytes == v3_bytes, "Minimal GI (LOCA+GEOL) must be byte-idempotent"
