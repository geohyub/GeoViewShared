"""
Converter round-trip tests — Phase A-3 Week 15 A3.4.

Covers two fixtures × four always-on formats = 8 round-trip tests,
plus format-inference + dispatch + assert_bundle_equal negative
checks. LAS fixture is optional (skipped when lasio is not
installed).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from geoview_cpt.ags_convert import (
    ProjectMeta,
    load_ags,
    write_ags,
    write_gi_ags,
)
from geoview_cpt.ags_convert.converters import (
    assert_bundle_equal,
    convert,
    from_csv,
    from_json,
    from_parquet,
    from_xlsx,
    to_csv,
    to_json,
    to_parquet,
    to_xlsx,
)
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding
from geoview_gi.minimal_model import Borehole, StratumLayer


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cpt_bundle(tmp_path):
    d = np.linspace(0.5, 5.0, 10)
    s = CPTSounding(handle=1, element_tag="", name="CPT01", max_depth_m=5.0)
    s.header = CPTHeader(
        sounding_id="CPT01",
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.8,
        loca_x=100.0,
        loca_y=200.0,
    )
    s.channels = {
        "depth": CPTChannel("depth", "m", d),
        "qc": CPTChannel("qc", "MPa", np.linspace(1.0, 5.0, 10)),
        "fs": CPTChannel("fs", "kPa", np.linspace(10.0, 50.0, 10)),
        "u2": CPTChannel("u2", "kPa", np.linspace(0.0, 20.0, 10)),
    }
    s.derived = {}
    out = tmp_path / "cpt.ags"
    write_ags(s, out, project_meta=ProjectMeta(project_id="P01", client="Geoview"))
    return load_ags(out)


@pytest.fixture
def gi_bundle(tmp_path):
    bh = Borehole(
        loca_id="BH-01",
        easting_m=100.0,
        northing_m=200.0,
        crs="EPSG:5186",
        ground_level_m=2.0,
        final_depth_m=10.0,
        start_date=date(2025, 10, 1),
        end_date=date(2025, 10, 2),
        method="Rotary Core",
    )
    bh.add_stratum(StratumLayer(top_m=0.0, base_m=3.0, description="sand", legend_code="SP"))
    bh.add_stratum(StratumLayer(top_m=3.0, base_m=10.0, description="clay", legend_code="CL"))
    out = tmp_path / "gi.ags"
    write_gi_ags(bh, out, project_meta=ProjectMeta(project_id="P01"))
    return load_ags(out)


# ---------------------------------------------------------------------------
# xlsx / csv / json / parquet — 2 fixtures × 4 formats = 8 round-trips
# ---------------------------------------------------------------------------


def test_xlsx_roundtrip_cpt(cpt_bundle, tmp_path):
    path = tmp_path / "cpt.xlsx"
    to_xlsx(cpt_bundle, path)
    loaded = from_xlsx(path)
    assert_bundle_equal(cpt_bundle, loaded)


def test_xlsx_roundtrip_gi(gi_bundle, tmp_path):
    path = tmp_path / "gi.xlsx"
    to_xlsx(gi_bundle, path)
    loaded = from_xlsx(path)
    assert_bundle_equal(gi_bundle, loaded)


def test_csv_roundtrip_cpt(cpt_bundle, tmp_path):
    target = tmp_path / "cpt_csv"
    to_csv(cpt_bundle, target)
    assert (target / "_manifest.json").exists()
    assert (target / "SCPT.csv").exists()
    loaded = from_csv(target)
    assert_bundle_equal(cpt_bundle, loaded)


def test_csv_roundtrip_gi(gi_bundle, tmp_path):
    target = tmp_path / "gi_csv"
    to_csv(gi_bundle, target)
    loaded = from_csv(target)
    assert_bundle_equal(gi_bundle, loaded)


def test_json_roundtrip_cpt(cpt_bundle, tmp_path):
    path = tmp_path / "cpt.json"
    to_json(cpt_bundle, path)
    loaded = from_json(path)
    assert_bundle_equal(cpt_bundle, loaded)
    # Schema version pinned
    import json as _json

    payload = _json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["order"][0] == "PROJ"


def test_json_roundtrip_gi(gi_bundle, tmp_path):
    path = tmp_path / "gi.json"
    to_json(gi_bundle, path)
    loaded = from_json(path)
    assert_bundle_equal(gi_bundle, loaded)


def test_parquet_roundtrip_cpt(cpt_bundle, tmp_path):
    target = tmp_path / "cpt_parquet"
    to_parquet(cpt_bundle, target)
    assert (target / "SCPT.parquet").exists()
    loaded = from_parquet(target)
    assert_bundle_equal(cpt_bundle, loaded)


def test_parquet_roundtrip_gi(gi_bundle, tmp_path):
    target = tmp_path / "gi_parquet"
    to_parquet(gi_bundle, target)
    loaded = from_parquet(target)
    assert_bundle_equal(gi_bundle, loaded)


# ---------------------------------------------------------------------------
# convert() dispatch and inference
# ---------------------------------------------------------------------------


def test_convert_ags_to_xlsx_and_back(cpt_bundle, tmp_path):
    ags_path = tmp_path / "src.ags"
    from geoview_cpt.ags_convert.wrapper import dump_ags

    dump_ags(cpt_bundle, ags_path)
    xlsx_path = tmp_path / "mid.xlsx"
    convert(ags_path, xlsx_path)
    back_path = tmp_path / "back.ags"
    convert(xlsx_path, back_path)
    loaded = load_ags(back_path)
    assert_bundle_equal(cpt_bundle, loaded)


def test_convert_explicit_formats(cpt_bundle, tmp_path):
    from geoview_cpt.ags_convert.wrapper import dump_ags

    src = tmp_path / "source.ags"
    dump_ags(cpt_bundle, src)
    dst = tmp_path / "out.unknown_ext"
    convert(src, dst, dst_format="json")
    assert dst.exists()
    loaded = from_json(dst)
    assert_bundle_equal(cpt_bundle, loaded)


def test_convert_unknown_format_raises(tmp_path):
    with pytest.raises(ValueError):
        convert(tmp_path / "a.ags", tmp_path / "b.xyz")


# ---------------------------------------------------------------------------
# assert_bundle_equal negative paths
# ---------------------------------------------------------------------------


def test_assert_bundle_equal_group_mismatch(cpt_bundle):
    from geoview_cpt.ags_convert.wrapper import AGSBundle

    subset = AGSBundle(
        tables={"PROJ": cpt_bundle.tables["PROJ"]},
        headings={"PROJ": list(cpt_bundle.tables["PROJ"].columns)},
    )
    with pytest.raises(AssertionError, match="group sets"):
        assert_bundle_equal(cpt_bundle, subset)


def test_assert_bundle_equal_value_mismatch(cpt_bundle, tmp_path):
    from geoview_cpt.ags_convert.wrapper import AGSBundle, dump_ags, load_ags

    dump_ags(cpt_bundle, tmp_path / "c.ags")
    other = load_ags(tmp_path / "c.ags")
    # Mutate a value
    other.tables["PROJ"].iat[2, 1] = "MODIFIED"
    with pytest.raises(AssertionError, match="PROJ.PROJ_ID values differ"):
        assert_bundle_equal(cpt_bundle, other)


# ---------------------------------------------------------------------------
# LAS — optional
# ---------------------------------------------------------------------------


def _has_lasio() -> bool:
    try:
        import lasio  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_lasio(), reason="lasio optional extra not installed")
def test_las_roundtrip_scpt_only(cpt_bundle, tmp_path):
    from geoview_cpt.ags_convert.converters.las_fmt import from_las, to_las

    out = tmp_path / "cpt.las"
    to_las(cpt_bundle, out)
    assert out.exists()
    loaded = from_las(out)
    assert "SCPT" in loaded.tables
    # LAS is lossy — only verify SCPT depth count survives
    scpt_src = cpt_bundle.tables["SCPT"].iloc[2:]
    scpt_dst = loaded.tables["SCPT"].iloc[2:]
    assert len(scpt_src) == len(scpt_dst)


def test_las_import_raises_without_lasio(tmp_path):
    if _has_lasio():
        pytest.skip("lasio installed — the error path is unreachable")
    from geoview_cpt.ags_convert.converters.las_fmt import to_las
    from geoview_cpt.ags_convert.wrapper import AgsConvertError

    with pytest.raises(AgsConvertError, match="lasio"):
        to_las(None, tmp_path / "x.las")
