"""
Tests for the Kingdom location CSV writer — Phase A-4 Week 17 A4.3.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.ags_convert import (
    ProjectMeta,
    load_ags,
    write_ags,
    write_gi_ags,
)
from geoview_cpt.ags_convert.kingdom import (
    LOCATION_COLUMNS,
    build_location_csv,
    build_location_csv_from_bundles,
)
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding
from geoview_gi.minimal_model import Borehole


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    return reader.fieldnames or [], rows


def _make_cpt(name: str, x: float, y: float, fdep: float = 5.0) -> CPTSounding:
    d = np.linspace(0.5, fdep, 6)
    s = CPTSounding(handle=1, element_tag="", name=name, max_depth_m=fdep)
    s.header = CPTHeader(
        sounding_id=name,
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.8,
        loca_x=x,
        loca_y=y,
        water_depth_m=18.5,
    )
    s.channels = {
        "depth": CPTChannel("depth", "m", d),
        "qc":    CPTChannel("qc", "MPa", np.linspace(1, 5, 6)),
        "fs":    CPTChannel("fs", "kPa", np.linspace(10, 50, 6)),
        "u2":    CPTChannel("u2", "kPa", np.linspace(0, 20, 6)),
    }
    s.derived = {}
    return s


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def test_location_columns_match_kingdom_schema():
    assert LOCATION_COLUMNS == (
        "LOCA_ID",
        "Easting",
        "Northing",
        "CRS",
        "GL_m",
        "Seabed_m",
        "Water_Depth_m",
        "Type",
        "Date",
        "Remarks",
    )


# ---------------------------------------------------------------------------
# build_location_csv (raw rows)
# ---------------------------------------------------------------------------


def test_build_location_csv_writes_header_only_when_empty(tmp_path):
    out = tmp_path / "empty.csv"
    build_location_csv([], out)
    header, rows = _read_csv(out)
    assert header == list(LOCATION_COLUMNS)
    assert rows == []


def test_build_location_csv_with_rows(tmp_path):
    out = tmp_path / "loc.csv"
    rows = [
        {
            "LOCA_ID": "BH-01",
            "Easting": "100.00",
            "Northing": "200.00",
            "CRS": "EPSG:5179",
            "GL_m": "2.50",
            "Seabed_m": "2.50",
            "Water_Depth_m": "10.00",
            "Type": "BH",
            "Date": "2025-10-01",
            "Remarks": "Rotary Core",
        }
    ]
    build_location_csv(rows, out)
    header, parsed = _read_csv(out)
    assert header == list(LOCATION_COLUMNS)
    assert len(parsed) == 1
    assert parsed[0]["LOCA_ID"] == "BH-01"
    assert parsed[0]["CRS"] == "EPSG:5179"


def test_build_location_csv_ignores_unknown_keys(tmp_path):
    out = tmp_path / "extra.csv"
    rows = [{"LOCA_ID": "BH-01", "CRS": "EPSG:5179", "BOGUS": "ignored"}]
    build_location_csv(rows, out)
    _, parsed = _read_csv(out)
    assert "BOGUS" not in parsed[0]
    assert parsed[0]["LOCA_ID"] == "BH-01"


def test_build_location_csv_creates_parent_dirs(tmp_path):
    out = tmp_path / "deep" / "nested" / "loc.csv"
    build_location_csv([], out)
    assert out.exists()


def test_build_location_csv_missing_keys_become_empty(tmp_path):
    out = tmp_path / "sparse.csv"
    rows = [{"LOCA_ID": "BH-01"}]
    build_location_csv(rows, out)
    _, parsed = _read_csv(out)
    assert parsed[0]["Easting"] == ""
    assert parsed[0]["CRS"] == ""


# ---------------------------------------------------------------------------
# build_location_csv_from_bundles (CPT path)
# ---------------------------------------------------------------------------


def test_location_from_single_cpt_bundle(tmp_path):
    s = _make_cpt("CPT01", 100.0, 200.0)
    write_ags(s, tmp_path / "src.ags",
              project_meta=ProjectMeta(project_id="P01", crs="EPSG:5179"))
    bundle = load_ags(tmp_path / "src.ags")
    out = tmp_path / "loc.csv"
    build_location_csv_from_bundles([bundle], out)
    _, parsed = _read_csv(out)
    assert len(parsed) == 1
    assert parsed[0]["LOCA_ID"] == "CPT01"
    assert parsed[0]["Easting"] == "100.00"
    assert parsed[0]["Northing"] == "200.00"
    assert parsed[0]["CRS"] == "EPSG:5179"


def test_location_from_multiple_cpt_bundles(tmp_path):
    bundles = []
    for i, (x, y) in enumerate([(100, 200), (300, 400), (500, 600)], start=1):
        name = f"CPT{i:02d}"
        s = _make_cpt(name, float(x), float(y))
        write_ags(s, tmp_path / f"{name}.ags",
                  project_meta=ProjectMeta(project_id="P01", crs="EPSG:5179"))
        bundles.append(load_ags(tmp_path / f"{name}.ags"))
    out = tmp_path / "all.csv"
    build_location_csv_from_bundles(bundles, out)
    _, parsed = _read_csv(out)
    assert len(parsed) == 3
    assert {row["LOCA_ID"] for row in parsed} == {"CPT01", "CPT02", "CPT03"}
    # All rows share the same CRS
    assert all(row["CRS"] == "EPSG:5179" for row in parsed)


def test_location_from_gi_borehole_bundle(tmp_path):
    bh = Borehole(
        loca_id="BH-01",
        easting_m=999.99,
        northing_m=888.88,
        crs="EPSG:32652",
        ground_level_m=2.5,
        final_depth_m=15.0,
        start_date=date(2025, 10, 1),
        method="Rotary Core",
    )
    write_gi_ags(bh, tmp_path / "gi.ags",
                 project_meta=ProjectMeta(project_id="P01"))
    bundle = load_ags(tmp_path / "gi.ags")
    out = tmp_path / "loc.csv"
    build_location_csv_from_bundles([bundle], out)
    _, parsed = _read_csv(out)
    assert len(parsed) == 1
    row = parsed[0]
    assert row["LOCA_ID"] == "BH-01"
    assert row["Easting"] == "999.99"
    assert row["CRS"] == "EPSG:32652"
    assert row["Type"] == "BH"
    assert row["Date"] == "2025-10-01"


def test_location_skips_bundles_without_loca(tmp_path):
    from geoview_cpt.ags_convert.wrapper import AGSBundle
    import pandas as pd

    fake = AGSBundle(
        tables={
            "PROJ": pd.DataFrame(
                [
                    {"HEADING": "UNIT", "PROJ_ID": ""},
                    {"HEADING": "TYPE", "PROJ_ID": "ID"},
                    {"HEADING": "DATA", "PROJ_ID": "P01"},
                ]
            ).astype(str)
        },
        headings={"PROJ": ["HEADING", "PROJ_ID"]},
    )
    out = tmp_path / "loc.csv"
    build_location_csv_from_bundles([fake], out)
    _, parsed = _read_csv(out)
    assert parsed == []  # nothing to write but header is present


def test_location_crs_passthrough_no_coordconverter(tmp_path):
    """Per Week 17 spec rule #3: location CSV must NOT touch CoordConverter.
    The CRS string is pass-through. Assert the writer doesn't transform
    coordinate values when the source CRS differs from a Kingdom default."""
    s = _make_cpt("CPT01", 700000.0, 4500000.0)
    s.header.loca_crs = "EPSG:32652"  # UTM 52N
    write_ags(s, tmp_path / "src.ags",
              project_meta=ProjectMeta(project_id="P01", crs="EPSG:32652"))
    bundle = load_ags(tmp_path / "src.ags")
    out = tmp_path / "loc.csv"
    build_location_csv_from_bundles([bundle], out)
    _, parsed = _read_csv(out)
    # Coordinates emitted exactly as written — UTM, not transformed
    assert parsed[0]["Easting"] == "700000.00"
    assert parsed[0]["Northing"] == "4500000.00"
    assert parsed[0]["CRS"] == "EPSG:32652"
