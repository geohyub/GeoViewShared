"""
Tests for geoview_cpt.ags_convert.writer — Week 14 A3.2 Part 2.

Covers:
- GEOL writer (from CPTSounding.strata and from Borehole.strata)
- SAMP writer (LabSample)
- ISPT writer (SPTTest + refusal flag)
- LOCA-from-Borehole adapter
- build_gi_bundle orchestrator
- write_gi_ags end-to-end + semantic round-trip
- on_missing='inject_default' with process defaults + YAML file
- HELMS YW-01 live fixture (skipif H: drive unavailable)
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from geoview_cpt.ags_convert import (
    AGSBundle,
    AgsConvertError,
    ProjectMeta,
    build_core_bundle,
    build_gi_bundle,
    load_ags,
    write_ags,
    write_gi_ags,
)
from geoview_cpt.ags_convert.defaults_config import (
    DEFAULTS_ENV_VAR,
    apply_defaults,
    clear_defaults_cache,
    clear_process_defaults,
    load_defaults_file,
    set_process_defaults,
)
from geoview_cpt.ags_convert.groups import (
    build_geol,
    build_ispt,
    build_loca_from_borehole,
    build_samp,
)
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding
from geoview_gi.minimal_model import Borehole, LabSample, SPTTest, StratumLayer


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _data_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[2:].reset_index(drop=True)


def _unit_row(df: pd.DataFrame) -> dict:
    return df.iloc[0].to_dict()


@pytest.fixture
def strata_list():
    return [
        StratumLayer(
            top_m=0.0,
            base_m=3.5,
            description="Fine sand, loose",
            legend_code="SP",
            geology_code="SW",
            age="Holocene",
        ),
        StratumLayer(
            top_m=3.5,
            base_m=10.0,
            description="Soft clay",
            legend_code="CL",
            geology_code="CL",
            age="Pleistocene",
            weathering_grade=2,
        ),
    ]


@pytest.fixture
def samples_list():
    return [
        LabSample(
            loca_id="BH-01",
            sample_id="S-01",
            sample_type="UT",
            sample_ref="UT-1",
            top_m=1.5,
            base_m=2.0,
            recovery_pct=95.0,
        ),
        LabSample(
            loca_id="BH-01",
            sample_id="S-02",
            sample_type="BT",
            top_m=4.0,
            base_m=4.5,
        ),
    ]


@pytest.fixture
def spt_list():
    return [
        SPTTest(top_m=2.0, seat_blows=5, main_blows=15, n_value=15, method="SPT"),
        SPTTest(
            top_m=5.0,
            seat_blows=10,
            main_blows=30,
            n_value=30,
            method="SPT(C)",
            refusal=True,
            remarks="hit rock",
        ),
    ]


@pytest.fixture
def borehole(strata_list, samples_list, spt_list):
    bh = Borehole(
        loca_id="BH-01",
        project_name="Week14",
        client="Geoview",
        easting_m=123456.78,
        northing_m=345678.90,
        crs="EPSG:5186",
        ground_level_m=2.5,
        final_depth_m=10.0,
        start_date=date(2025, 10, 1),
        end_date=date(2025, 10, 3),
        method="Rotary Core",
    )
    for layer in strata_list:
        bh.add_stratum(layer)
    for samp in samples_list:
        bh.add_sample(samp)
    for spt in spt_list:
        bh.add_spt(spt)
    return bh


# ---------------------------------------------------------------------------
# GEOL writer
# ---------------------------------------------------------------------------


def test_geol_from_strata_list(strata_list):
    df = build_geol("BH-01", strata_list)
    data = _data_rows(df)
    assert len(data) == 2
    assert data.iloc[0]["LOCA_ID"] == "BH-01"
    assert data.iloc[0]["GEOL_TOP"] == "0.00"
    assert data.iloc[0]["GEOL_BASE"] == "3.50"
    assert data.iloc[0]["GEOL_LEG"] == "SP"
    assert data.iloc[0]["GEOL_GEOL"] == "SW"
    assert data.iloc[0]["GEOL_GEO2"] == "Holocene"
    assert data.iloc[1]["GEOL_STAT"] == "2"


def test_geol_empty_strata():
    df = build_geol("BH-01", [])
    data = _data_rows(df)
    assert len(data) == 0
    assert list(df.columns)[0] == "HEADING"
    # Still valid UNIT/TYPE rows
    assert df.iloc[0]["GEOL_TOP"] == "m"


def test_geol_units_and_types():
    df = build_geol("BH-01", [StratumLayer(top_m=0.0, base_m=1.0)])
    assert _unit_row(df)["GEOL_TOP"] == "m"
    assert _unit_row(df)["GEOL_BASE"] == "m"
    assert df.iloc[1]["GEOL_TOP"] == "2DP"
    assert df.iloc[1]["GEOL_LEG"] == "PA"


def test_geol_weathering_none_blank():
    df = build_geol("BH-01", [StratumLayer(top_m=0.0, base_m=1.0)])
    data = _data_rows(df)
    assert data.iloc[0]["GEOL_STAT"] == ""


# ---------------------------------------------------------------------------
# SAMP writer
# ---------------------------------------------------------------------------


def test_samp_basic(samples_list):
    df = build_samp(samples_list)
    data = _data_rows(df)
    assert len(data) == 2
    row = data.iloc[0]
    assert row["LOCA_ID"] == "BH-01"
    assert row["SAMP_ID"] == "S-01"
    assert row["SAMP_TYPE"] == "UT"
    assert row["SAMP_REF"] == "UT-1"
    assert row["SAMP_TOP"] == "1.50"
    assert row["SAMP_BASE"] == "2.00"
    assert row["SAMP_RECV"] == "95"


def test_samp_blank_base_recovery(samples_list):
    df = build_samp([samples_list[1]])
    data = _data_rows(df)
    assert data.iloc[0]["SAMP_BASE"] == "4.50"
    assert data.iloc[0]["SAMP_RECV"] == ""


def test_samp_empty():
    df = build_samp([])
    assert len(_data_rows(df)) == 0


# ---------------------------------------------------------------------------
# ISPT writer
# ---------------------------------------------------------------------------


def test_ispt_basic(spt_list):
    df = build_ispt("BH-01", spt_list)
    data = _data_rows(df)
    assert len(data) == 2
    row0 = data.iloc[0]
    assert row0["LOCA_ID"] == "BH-01"
    assert row0["ISPT_TOP"] == "2.00"
    assert row0["ISPT_SEAT"] == "5"
    assert row0["ISPT_MAIN"] == "15"
    assert row0["ISPT_NVAL"] == "15"
    assert row0["ISPT_METH"] == "SPT"
    assert row0["ISPT_REM"] == ""


def test_ispt_refusal_in_remarks(spt_list):
    df = build_ispt("BH-01", [spt_list[1]])
    data = _data_rows(df)
    row = data.iloc[0]
    assert row["ISPT_METH"] == "SPT(C)"
    assert "REFUSAL" in row["ISPT_REM"]
    assert "hit rock" in row["ISPT_REM"]


def test_ispt_none_blows_blank():
    df = build_ispt("BH-01", [SPTTest(top_m=1.0)])
    data = _data_rows(df)
    row = data.iloc[0]
    assert row["ISPT_SEAT"] == ""
    assert row["ISPT_MAIN"] == ""
    assert row["ISPT_NVAL"] == ""


# ---------------------------------------------------------------------------
# LOCA-from-Borehole adapter
# ---------------------------------------------------------------------------


def test_loca_from_borehole_maps_fields(borehole):
    df = build_loca_from_borehole(borehole)
    data = _data_rows(df)
    row = data.iloc[0]
    assert row["LOCA_ID"] == "BH-01"
    assert row["LOCA_TYPE"] == "BH"  # default for borehole path
    assert row["LOCA_NATE"] == "123456.78"
    assert row["LOCA_NATN"] == "345678.90"
    assert row["LOCA_GREF"] == "EPSG:5186"
    assert row["LOCA_GL"] == "2.50"
    assert row["LOCA_FDEP"] == "10.00"
    assert row["LOCA_STAR"] == "2025-10-01"
    assert row["LOCA_ENDD"] == "2025-10-03"
    # W1 fix: LOCA_CLNT dropped — client lives in PROJ_CLNT.
    assert "LOCA_CLNT" not in df.columns
    assert row["LOCA_PURP"] == "Rotary Core"  # method fallback


def test_loca_from_borehole_meta_overrides_purpose(borehole):
    meta = ProjectMeta(loca_purpose="Wind farm SI", crs="EPSG:4326")
    df = build_loca_from_borehole(borehole, meta)
    data = _data_rows(df)
    row = data.iloc[0]
    assert row["LOCA_PURP"] == "Wind farm SI"
    # borehole CRS wins over meta.crs (adapter sources real value first)
    assert row["LOCA_GREF"] == "EPSG:5186"


def test_loca_from_borehole_fallback_crs_from_meta():
    bh = Borehole(loca_id="B2")
    df = build_loca_from_borehole(bh, ProjectMeta(crs="EPSG:4326", client="C"))
    data = _data_rows(df)
    assert data.iloc[0]["LOCA_GREF"] == "EPSG:4326"
    # W1 fix: client lives in PROJ_CLNT, not LOCA
    assert "LOCA_CLNT" not in df.columns


# ---------------------------------------------------------------------------
# build_gi_bundle
# ---------------------------------------------------------------------------


def test_gi_bundle_full(borehole):
    bundle = build_gi_bundle(borehole, project_meta=ProjectMeta(project_id="P01"))
    assert isinstance(bundle, AGSBundle)
    assert {"PROJ", "TRAN", "UNIT", "TYPE", "LOCA", "GEOL", "SAMP", "ISPT"} <= set(
        bundle.tables.keys()
    )
    assert len(_data_rows(bundle.tables["GEOL"])) == 2
    assert len(_data_rows(bundle.tables["SAMP"])) == 2
    assert len(_data_rows(bundle.tables["ISPT"])) == 2


def test_gi_bundle_empty_layers_omits_groups():
    bh = Borehole(loca_id="BH-empty", easting_m=0.0, northing_m=0.0)
    bundle = build_gi_bundle(bh)
    assert "GEOL" not in bundle.tables
    assert "SAMP" not in bundle.tables
    assert "ISPT" not in bundle.tables
    assert {"PROJ", "TRAN", "UNIT", "TYPE", "LOCA"} <= set(bundle.tables.keys())


def test_gi_bundle_unit_collection(borehole):
    bundle = build_gi_bundle(borehole)
    units = set(_data_rows(bundle.tables["UNIT"])["UNIT_UNIT"])
    assert "m" in units  # from GEOL/LOCA


def test_write_gi_ags_roundtrip(tmp_path, borehole):
    out = tmp_path / "gi.ags"
    write_gi_ags(borehole, out, project_meta=ProjectMeta(project_id="P01"))
    assert out.exists()
    loaded = load_ags(out)
    assert "GEOL" in loaded.tables
    assert "ISPT" in loaded.tables
    geol_data = _data_rows(loaded.tables["GEOL"])
    assert len(geol_data) == 2
    assert geol_data.iloc[0]["GEOL_LEG"] == "SP"
    assert geol_data.iloc[1]["GEOL_STAT"] == "2"
    ispt_data = _data_rows(loaded.tables["ISPT"])
    assert "REFUSAL" in ispt_data.iloc[1]["ISPT_REM"]


# ---------------------------------------------------------------------------
# GEOL inside build_core_bundle (CPT with strata attached)
# ---------------------------------------------------------------------------


def _cpt_with_strata(strata: list[StratumLayer]) -> CPTSounding:
    d = np.linspace(0.5, 5.0, 10)
    s = CPTSounding(handle=1, element_tag="", name="CPT01", max_depth_m=5.0)
    s.header = CPTHeader(
        sounding_id="CPT01",
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.8,
    )
    s.channels = {
        "depth": CPTChannel("depth", "m", d),
        "qc": CPTChannel("qc", "MPa", np.linspace(1.0, 5.0, 10)),
        "fs": CPTChannel("fs", "kPa", np.linspace(10.0, 50.0, 10)),
        "u2": CPTChannel("u2", "kPa", np.linspace(0.0, 20.0, 10)),
    }
    s.derived = {}
    s.strata = strata
    return s


def test_core_bundle_includes_geol_when_strata(strata_list):
    s = _cpt_with_strata(strata_list)
    bundle = build_core_bundle(s, project_meta=ProjectMeta(project_id="P01"))
    assert "GEOL" in bundle.tables
    geol_data = _data_rows(bundle.tables["GEOL"])
    assert len(geol_data) == 2
    assert geol_data.iloc[0]["LOCA_ID"] == "CPT01"


def test_core_bundle_no_geol_when_empty_strata():
    s = _cpt_with_strata([])
    bundle = build_core_bundle(s)
    assert "GEOL" not in bundle.tables


def test_core_bundle_cpt_geol_roundtrip(tmp_path, strata_list):
    s = _cpt_with_strata(strata_list)
    out = tmp_path / "cpt_geol.ags"
    write_ags(s, out, project_meta=ProjectMeta(project_id="P01"))
    loaded = load_ags(out)
    assert "GEOL" in loaded.tables
    geol = _data_rows(loaded.tables["GEOL"])
    assert geol.iloc[0]["GEOL_LEG"] == "SP"


# ---------------------------------------------------------------------------
# defaults_config (on_missing='inject_default')
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_defaults_state():
    clear_process_defaults()
    clear_defaults_cache()
    os.environ.pop(DEFAULTS_ENV_VAR, None)
    yield
    clear_process_defaults()
    clear_defaults_cache()
    os.environ.pop(DEFAULTS_ENV_VAR, None)


def test_apply_defaults_none_meta():
    set_process_defaults({"project_id": "P", "client": "C"})
    meta = apply_defaults(None)
    assert meta.project_id == "P"
    assert meta.client == "C"


def test_apply_defaults_caller_wins():
    set_process_defaults({"project_id": "FROM_DEFAULTS", "client": "FROM_DEFAULTS"})
    meta = apply_defaults(ProjectMeta(project_id="USER"))
    assert meta.project_id == "USER"
    assert meta.client == "FROM_DEFAULTS"


def test_apply_defaults_no_source_returns_unchanged():
    meta = ProjectMeta(project_id="X")
    assert apply_defaults(meta) is meta
    assert apply_defaults(None).project_id == ""


def test_apply_defaults_unknown_key_raises():
    with pytest.raises(AgsConvertError, match="unknown"):
        set_process_defaults({"bogus_field": "x"})


def test_load_defaults_file_yaml(tmp_path):
    cfg = tmp_path / "defaults.yaml"
    cfg.write_text(
        "project_id: P01\nclient: Geoview\ncrs: EPSG:5186\n",
        encoding="utf-8",
    )
    data = load_defaults_file(cfg)
    assert data["project_id"] == "P01"
    assert data["crs"] == "EPSG:5186"


def test_env_based_defaults(tmp_path):
    cfg = tmp_path / "d.yaml"
    cfg.write_text("project_id: FROM_ENV\n", encoding="utf-8")
    os.environ[DEFAULTS_ENV_VAR] = str(cfg)
    meta = apply_defaults(None)
    assert meta.project_id == "FROM_ENV"


def test_writer_uses_inject_default(tmp_path, borehole):
    set_process_defaults({"project_id": "INJECTED", "client": "Geoview"})
    out = tmp_path / "inj.ags"
    write_gi_ags(borehole, out, on_missing="inject_default")
    loaded = load_ags(out)
    proj = _data_rows(loaded.tables["PROJ"])
    assert proj.iloc[0]["PROJ_ID"] == "INJECTED"
    assert proj.iloc[0]["PROJ_CLNT"] == "Geoview"


def test_writer_prompt_still_raises(tmp_path, borehole):
    out = tmp_path / "p.ags"
    with pytest.raises(NotImplementedError, match="prompt"):
        write_gi_ags(borehole, out, on_missing="prompt")


# ---------------------------------------------------------------------------
# HELMS YW-01 (H: drive) — real data round trip
# ---------------------------------------------------------------------------


def _yw01_path() -> Path | None:
    base = Path("H:/야월해상풍력단지 지반조사 용역 결과보고서_rev7/CPT 데이터 분석/Raw_Data")
    if not base.exists():
        return None
    for pattern in ("YW-01*.xlsx", "YW-01*.xls"):
        for p in base.glob(pattern):
            return p
    return None


@pytest.mark.skipif(_yw01_path() is None, reason="HELMS YW-01 fixture not available")
def test_write_ags_helms_yw01(tmp_path):
    from geoview_cpt.parsers import parse_yw_xlsx

    src = _yw01_path()
    assert src is not None
    result = parse_yw_xlsx(src)
    sounding = result if isinstance(result, CPTSounding) else result.soundings[0]
    out = tmp_path / "yw01.ags"
    write_ags(sounding, out, project_meta=ProjectMeta(project_id="HELMS"))
    assert out.exists()
    loaded = load_ags(out)
    assert "SCPT" in loaded.tables
    data = _data_rows(loaded.tables["SCPT"])
    assert len(data) > 0
