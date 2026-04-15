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

Week 14 scope: 2 samples — one synthetic JAKO-style CPT and one
real HELMS YW-01 pcpt (skipped when H: drive unavailable). The
remaining 3 samples land in Week 15 A3.4 when the xlsx/csv/las
converters expose their own fixtures.
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
