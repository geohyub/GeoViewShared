"""Tests for geoview_cpt.ags_convert.writer — Phase A-3 Week 13 A3.2."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from geoview_cpt.ags_convert import (
    AGSBundle,
    ProjectMeta,
    build_core_bundle,
    dump_ags,
    load_ags,
    write_ags,
)
from geoview_cpt.ags_convert.groups import (
    build_loca,
    build_proj,
    build_scpg,
    build_scpp,
    build_scpt,
    build_tran,
    build_type_dictionary,
    build_unit_dictionary,
)
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding

CORE_GROUPS = {"PROJ", "TRAN", "UNIT", "TYPE", "LOCA", "SCPG", "SCPT", "SCPP"}


# ---------------------------------------------------------------------------
# Synthetic sounding fixture
# ---------------------------------------------------------------------------


def _make_sounding(name: str = "CPT01", n: int = 10) -> CPTSounding:
    depth = np.linspace(0.5, 5.0, n)
    qc = np.linspace(1.0, 5.0, n)     # MPa
    fs = np.linspace(10.0, 50.0, n)   # kPa
    u2 = np.linspace(0.0, 20.0, n)    # kPa
    qt = qc + 0.1
    fr = np.linspace(0.5, 2.5, n)     # %
    bq = np.linspace(0.01, 0.1, n)
    ic = np.linspace(1.5, 3.0, n)

    s = CPTSounding(handle=1, element_tag="", name=name, max_depth_m=float(depth[-1]))
    s.header = CPTHeader(
        sounding_id=name,
        project_name="JAKO",
        client="Geoview",
        loca_x=123456.78,
        loca_y=345678.90,
        water_depth_m=18.5,
        max_push_depth_m=float(depth[-1]),
        equipment_model="Gouda WISON",
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.8,
        started_at=datetime(2025, 10, 1, 9, 0, 0),
        completed_at=datetime(2025, 10, 1, 10, 30, 0),
    )
    s.channels = {
        "depth": CPTChannel("depth", "m",   depth),
        "qc":    CPTChannel("qc",    "MPa", qc),
        "fs":    CPTChannel("fs",    "kPa", fs),
        "u2":    CPTChannel("u2",    "kPa", u2),
    }
    s.derived = {
        "qt": CPTChannel("qt", "MPa", qt),
        "Fr": CPTChannel("Fr", "%",   fr),
        "Bq": CPTChannel("Bq", "",    bq),
        "Ic": CPTChannel("Ic", "",    ic),
    }
    return s


@pytest.fixture
def sounding() -> CPTSounding:
    return _make_sounding()


@pytest.fixture
def meta() -> ProjectMeta:
    return ProjectMeta(
        project_id="P01",
        project_name="JAKO Marine CPT",
        project_location="Offshore Korea",
        client="Geoview",
        contractor="Gouda",
        engineer="Hyub",
        crs="EPSG:5186",
        loca_type="CPT",
        loca_status="FINAL",
        loca_purpose="Wind farm site investigation",
        tran_status="DRAFT",
        tran_recipient="Geoview",
    )


# ---------------------------------------------------------------------------
# ProjectMeta
# ---------------------------------------------------------------------------


def test_project_meta_from_dict_filters_unknown_keys():
    meta = ProjectMeta.from_dict(
        {"project_id": "P01", "client": "Geoview", "not_a_field": "xxx"}
    )
    assert meta.project_id == "P01"
    assert meta.client == "Geoview"


def test_project_meta_defaults_are_blank():
    meta = ProjectMeta()
    assert meta.project_id == ""
    assert meta.tran_status == "DRAFT"
    assert meta.tran_issue_no == "1"


# ---------------------------------------------------------------------------
# Individual GROUP builders
# ---------------------------------------------------------------------------


def _unit_row(df: pd.DataFrame) -> dict:
    return df.iloc[0].to_dict()


def _type_row(df: pd.DataFrame) -> dict:
    return df.iloc[1].to_dict()


def _data_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[2:].reset_index(drop=True)


def test_build_proj_populated(meta):
    df = build_proj(meta)
    assert df.shape == (3, 8)
    assert list(df.columns)[0] == "HEADING"
    assert _unit_row(df)["HEADING"] == "UNIT"
    assert _type_row(df)["HEADING"] == "TYPE"
    data = _data_rows(df)
    assert data.iloc[0]["PROJ_ID"] == "P01"
    assert data.iloc[0]["PROJ_CLNT"] == "Geoview"


def test_build_proj_blank_when_none():
    df = build_proj(None)
    data = _data_rows(df)
    assert data.iloc[0]["PROJ_ID"] == ""
    assert data.iloc[0]["PROJ_NAME"] == ""


def test_build_tran_defaults():
    df = build_tran()
    data = _data_rows(df)
    assert data.iloc[0]["TRAN_ISNO"] == "1"
    assert data.iloc[0]["TRAN_AGS"] == "4.1"
    assert data.iloc[0]["TRAN_STAT"] == "DRAFT"
    assert data.iloc[0]["TRAN_DLIM"] == '"'
    assert data.iloc[0]["TRAN_RCON"] == ","
    # TRAN_DATE must be ISO
    assert len(data.iloc[0]["TRAN_DATE"]) == 10
    assert data.iloc[0]["TRAN_DATE"][4] == "-"


def test_build_tran_overrides():
    df = build_tran(
        issue_no="5",
        status="FINAL",
        description="JAKO Week 13",
        recipient="Client",
    )
    data = _data_rows(df)
    assert data.iloc[0]["TRAN_ISNO"] == "5"
    assert data.iloc[0]["TRAN_STAT"] == "FINAL"
    assert data.iloc[0]["TRAN_DESC"] == "JAKO Week 13"
    assert data.iloc[0]["TRAN_RECV"] == "Client"


def test_build_loca_from_header(sounding, meta):
    df = build_loca(sounding, meta)
    data = _data_rows(df)
    row = data.iloc[0]
    assert row["LOCA_ID"] == "CPT01"
    assert row["LOCA_NATE"] == "123456.78"
    assert row["LOCA_NATN"] == "345678.90"
    assert row["LOCA_GL"] == "18.50"
    assert row["LOCA_FDEP"] == "5.00"
    assert row["LOCA_CLNT"] == "Geoview"
    assert row["LOCA_GREF"] == "EPSG:5186"
    assert row["LOCA_STAR"] == "2025-10-01"
    assert row["LOCA_ENDD"] == "2025-10-01"


def test_build_loca_without_meta(sounding):
    df = build_loca(sounding, None)
    data = _data_rows(df)
    row = data.iloc[0]
    assert row["LOCA_ID"] == "CPT01"
    assert row["LOCA_CLNT"] == ""
    assert row["LOCA_GREF"] == ""


def test_build_scpg_populated(sounding):
    df = build_scpg(sounding)
    data = _data_rows(df)
    row = data.iloc[0]
    assert row["LOCA_ID"] == "CPT01"
    assert row["SCPG_TYPE"] == "Gouda WISON"
    assert row["SCPG_CARD"] == "1000.00"
    assert row["SCPG_CAR"] == "0.800"
    assert row["SCPG_TESD"] == "2025-10-01"


def test_build_scpt_row_count_and_units(sounding):
    df = build_scpt(sounding)
    data = _data_rows(df)
    assert len(data) == 10
    # Unit row
    units = _unit_row(df)
    assert units["SCPT_DPTH"] == "m"
    assert units["SCPT_RES"] == "MN/m2"
    assert units["SCPT_FRES"] == "kN/m2"
    assert units["SCPT_PWP2"] == "kN/m2"
    assert units["SCPT_QT"] == "MN/m2"
    # First data row
    row0 = data.iloc[0]
    assert row0["LOCA_ID"] == "CPT01"
    assert row0["SCPT_DPTH"] == "0.50"
    assert row0["SCPT_RES"] == "1.00"  # qc MPa as-is
    assert row0["SCPT_FRES"] == "10.00"  # fs kPa as-is
    assert row0["SCPT_BQ"] == "0.010"


def test_build_scpt_unit_conversion_mpa_source():
    """qc supplied in kPa should be converted to MPa."""
    s = _make_sounding()
    s.channels["qc"] = CPTChannel("qc", "kPa", np.array([1000.0, 2000.0, 3000.0]))
    s.channels["depth"] = CPTChannel("depth", "m", np.array([1.0, 2.0, 3.0]))
    s.channels["fs"] = CPTChannel("fs", "kPa", np.array([10.0, 20.0, 30.0]))
    s.channels["u2"] = CPTChannel("u2", "kPa", np.array([0.0, 5.0, 10.0]))
    s.derived = {}
    df = build_scpt(s)
    data = _data_rows(df)
    # 1000 kPa = 1.00 MPa
    assert data.iloc[0]["SCPT_RES"] == "1.00"
    assert data.iloc[1]["SCPT_RES"] == "2.00"


def test_build_scpp_nkt_default(sounding):
    df = build_scpp(sounding)
    data = _data_rows(df)
    assert len(data) == 10
    assert data.iloc[0]["SCPP_NKT"] == "15.00"
    assert data.iloc[0]["SCPP_IC"] == "1.500"


def test_build_scpp_custom_nkt(sounding):
    df = build_scpp(sounding, default_nkt=30.0)
    data = _data_rows(df)
    assert data.iloc[0]["SCPP_NKT"] == "30.00"


def test_unit_dictionary_sorted():
    df = build_unit_dictionary({"m", "kPa", "MPa", "MN/m2"})
    data = _data_rows(df)
    units = list(data["UNIT_UNIT"])
    assert units == sorted(units)
    assert "m" in units
    # Known units get canonical descriptions
    m_row = data[data["UNIT_UNIT"] == "m"].iloc[0]
    assert m_row["UNIT_DESC"] == "metre"


def test_unit_dictionary_unknown_fallback():
    df = build_unit_dictionary({"bogus_unit"})
    data = _data_rows(df)
    row = data[data["UNIT_UNIT"] == "bogus_unit"].iloc[0]
    assert row["UNIT_DESC"] == "bogus_unit"


def test_type_dictionary_contains_core():
    df = build_type_dictionary({"ID", "X", "2DP", "DT"})
    data = _data_rows(df)
    types = set(data["TYPE_TYPE"])
    assert {"ID", "X", "2DP", "DT"} <= types


# ---------------------------------------------------------------------------
# build_core_bundle orchestrator
# ---------------------------------------------------------------------------


def test_build_core_bundle_all_groups(sounding, meta):
    bundle = build_core_bundle(sounding, project_meta=meta)
    assert isinstance(bundle, AGSBundle)
    assert set(bundle.tables.keys()) == CORE_GROUPS
    assert set(bundle.headings.keys()) == CORE_GROUPS


def test_build_core_bundle_accepts_dict(sounding):
    bundle = build_core_bundle(
        sounding, project_meta={"project_id": "P01", "client": "Geoview"}
    )
    data = _data_rows(bundle.tables["PROJ"])
    assert data.iloc[0]["PROJ_ID"] == "P01"


def test_build_core_bundle_none_meta(sounding):
    bundle = build_core_bundle(sounding, project_meta=None)
    assert set(bundle.tables.keys()) == CORE_GROUPS
    data = _data_rows(bundle.tables["PROJ"])
    assert data.iloc[0]["PROJ_ID"] == ""


def test_build_core_bundle_bad_meta_type(sounding):
    with pytest.raises(TypeError):
        build_core_bundle(sounding, project_meta=123)


def test_build_core_bundle_prompt_unsupported(sounding):
    with pytest.raises(NotImplementedError, match="prompt"):
        build_core_bundle(sounding, on_missing="prompt")


def test_build_core_bundle_inject_default_ships(sounding):
    """Week 14: inject_default is implemented (no defaults → same as omit)."""
    bundle = build_core_bundle(sounding, on_missing="inject_default")
    assert CORE_GROUPS <= set(bundle.tables.keys())


def test_build_core_bundle_invalid_policy(sounding):
    with pytest.raises(ValueError):
        build_core_bundle(sounding, on_missing="garbage")  # type: ignore[arg-type]


def test_build_core_bundle_collects_used_units(sounding, meta):
    bundle = build_core_bundle(sounding, project_meta=meta)
    unit_data = _data_rows(bundle.tables["UNIT"])
    units = set(unit_data["UNIT_UNIT"])
    # SCPT carries MN/m2, kN/m2, m ; LOCA carries m, yyyy-mm-dd ; SCPG has mm2, s
    assert "m" in units
    assert "MN/m2" in units
    assert "kN/m2" in units
    assert "yyyy-mm-dd" in units


def test_build_core_bundle_collects_used_types(sounding, meta):
    bundle = build_core_bundle(sounding, project_meta=meta)
    type_data = _data_rows(bundle.tables["TYPE"])
    types = set(type_data["TYPE_TYPE"])
    assert {"ID", "X", "2DP", "DT"} <= types


# ---------------------------------------------------------------------------
# write_ags — end-to-end file output + semantic round-trip
# ---------------------------------------------------------------------------


def test_write_ags_creates_file(tmp_path, sounding, meta):
    out = tmp_path / "jako.ags"
    returned = write_ags(sounding, out, project_meta=meta)
    assert returned == out
    assert out.exists()
    assert out.stat().st_size > 500


def test_write_ags_creates_parent_dirs(tmp_path, sounding, meta):
    out = tmp_path / "nested" / "dir" / "jako.ags"
    write_ags(sounding, out, project_meta=meta)
    assert out.exists()


def test_write_ags_prompt_policy_raises(tmp_path, sounding):
    from geoview_cpt.ags_convert.wrapper import AgsConvertError

    out = tmp_path / "x.ags"
    with pytest.raises((NotImplementedError, AgsConvertError)):
        write_ags(sounding, out, on_missing="prompt")


def test_write_ags_semantic_round_trip(tmp_path, sounding, meta):
    out = tmp_path / "rt.ags"
    write_ags(sounding, out, project_meta=meta)
    loaded = load_ags(out)
    assert CORE_GROUPS <= set(loaded.tables.keys())
    # PROJ fields preserved
    proj_data = _data_rows(loaded.tables["PROJ"])
    assert proj_data.iloc[0]["PROJ_ID"] == "P01"
    assert proj_data.iloc[0]["PROJ_CLNT"] == "Geoview"
    # LOCA preserved
    loca_data = _data_rows(loaded.tables["LOCA"])
    assert loca_data.iloc[0]["LOCA_ID"] == "CPT01"
    assert loca_data.iloc[0]["LOCA_NATE"] == "123456.78"
    # SCPT row count preserved
    scpt_data = _data_rows(loaded.tables["SCPT"])
    assert len(scpt_data) == 10
    assert scpt_data.iloc[0]["SCPT_DPTH"] == "0.50"
    assert scpt_data.iloc[-1]["SCPT_DPTH"] == "5.00"
    # SCPP Nkt preserved
    scpp_data = _data_rows(loaded.tables["SCPP"])
    assert scpp_data.iloc[0]["SCPP_NKT"] == "15.00"


def test_write_ags_omit_blank_when_no_meta(tmp_path, sounding):
    out = tmp_path / "blank.ags"
    write_ags(sounding, out)  # no project_meta
    loaded = load_ags(out)
    proj_data = _data_rows(loaded.tables["PROJ"])
    assert proj_data.iloc[0]["PROJ_ID"] == ""
    assert proj_data.iloc[0]["PROJ_NAME"] == ""
    loca_data = _data_rows(loaded.tables["LOCA"])
    assert loca_data.iloc[0]["LOCA_CLNT"] == ""
    assert loca_data.iloc[0]["LOCA_GREF"] == ""


def test_write_ags_unit_row_survives_round_trip(tmp_path, sounding, meta):
    out = tmp_path / "units.ags"
    write_ags(sounding, out, project_meta=meta)
    loaded = load_ags(out)
    scpt = loaded.tables["SCPT"]
    unit_row = scpt.iloc[0]
    assert unit_row["SCPT_RES"] == "MN/m2"
    assert unit_row["SCPT_FRES"] == "kN/m2"
    assert unit_row["SCPT_DPTH"] == "m"


# ---------------------------------------------------------------------------
# Real JAKO CPT01 (H: drive) — skipped when fixture unavailable
# ---------------------------------------------------------------------------


def _jako_cpt01_xls() -> Path | None:
    base = Path("H:/자코")
    if not base.exists():
        return None
    for p in base.rglob("*.xls*"):
        name = p.stem.upper()
        if "CPT01" in name or "CPT-01" in name:
            return p
    return None


@pytest.mark.skipif(
    _jako_cpt01_xls() is None, reason="JAKO CPT01 xls fixture not available"
)
def test_write_ags_real_jako_cpt01(tmp_path):
    from geoview_cpt.parsers import parse_jako_xls

    path = _jako_cpt01_xls()
    assert path is not None
    result = parse_jako_xls(path)
    soundings = getattr(result, "soundings", None) or [result]
    sounding = soundings[0]
    out = tmp_path / "jako_cpt01.ags"
    write_ags(sounding, out, project_meta=ProjectMeta(project_name="JAKO"))
    assert out.exists()
    loaded = load_ags(out)
    assert CORE_GROUPS <= set(loaded.tables.keys())
