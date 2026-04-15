"""
Tests for the Kingdom AGS4 subset filter — Phase A-4 Week 16 A4.0.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from geoview_cpt.ags_convert import (
    AGSBundle,
    AgsConvertError,
    ProjectMeta,
    load_ags,
    write_ags,
    write_gi_ags,
)
from geoview_cpt.ags_convert.kingdom import (
    DEFAULT_KINGDOM_CRS,
    EXCLUDED_GROUPS,
    KINGDOM_GROUPS,
    build_kingdom_subset,
    write_kingdom_ags,
)
from geoview_cpt.ags_convert.validator import Severity, validate_file
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding
from geoview_gi.minimal_model import (
    Borehole,
    LabSample,
    SPTTest,
    StratumLayer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_cpt_with_strata(name: str = "CPT01") -> CPTSounding:
    d = np.linspace(0.5, 5.0, 10)
    s = CPTSounding(handle=1, element_tag="", name=name, max_depth_m=5.0)
    s.header = CPTHeader(
        sounding_id=name,
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.8,
        loca_x=100.0,
        loca_y=200.0,
    )
    s.channels = {
        "depth": CPTChannel("depth", "m", d),
        "qc":    CPTChannel("qc", "MPa", np.linspace(1.0, 5.0, 10)),
        "fs":    CPTChannel("fs", "kPa", np.linspace(10.0, 50.0, 10)),
        "u2":    CPTChannel("u2", "kPa", np.linspace(0.0, 20.0, 10)),
    }
    s.derived = {"Ic": CPTChannel("Ic", "", np.linspace(1.5, 3.0, 10))}
    s.strata = [
        StratumLayer(top_m=0.0, base_m=2.5, description="sand", legend_code="SP"),
        StratumLayer(top_m=2.5, base_m=5.0, description="clay", legend_code="CL"),
    ]
    return s


@pytest.fixture
def cpt_bundle(tmp_path):
    s = _make_cpt_with_strata()
    out = tmp_path / "src.ags"
    write_ags(s, out, project_meta=ProjectMeta(project_id="P01", client="Geoview", crs="EPSG:5179"))
    return load_ags(out)


@pytest.fixture
def gi_bundle(tmp_path):
    """Mixed bundle with HOLE/SAMP/ISPT — tests filter exclusion."""
    bh = Borehole(
        loca_id="BH-01",
        easting_m=100.0,
        northing_m=200.0,
        crs="EPSG:5179",
        ground_level_m=2.0,
        final_depth_m=10.0,
        start_date=date(2025, 10, 1),
        method="Rotary Core",
    )
    bh.add_stratum(StratumLayer(top_m=0.0, base_m=3.0, description="sand", legend_code="SP"))
    bh.add_spt(SPTTest(top_m=2.0, main_blows=15, n_value=15))
    bh.add_sample(LabSample(loca_id="BH-01", sample_id="S-01", sample_type="UT", top_m=1.5, base_m=2.0))
    out = tmp_path / "gi.ags"
    write_gi_ags(bh, out, project_meta=ProjectMeta(project_id="P01"))
    return load_ags(out)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def test_kingdom_groups_in_canonical_order():
    assert KINGDOM_GROUPS == (
        "PROJ", "TRAN", "UNIT", "TYPE",
        "LOCA", "SCPG", "SCPT", "SCPP", "GEOL",
    )


def test_excluded_groups_set():
    assert EXCLUDED_GROUPS == frozenset({"HOLE", "SAMP", "ISPT"})


def test_default_kingdom_crs_present():
    assert "EPSG:5179" in DEFAULT_KINGDOM_CRS
    assert "EPSG:4326" in DEFAULT_KINGDOM_CRS


# ---------------------------------------------------------------------------
# build_kingdom_subset — happy path
# ---------------------------------------------------------------------------


def test_subset_keeps_kingdom_groups(cpt_bundle):
    subset = build_kingdom_subset(cpt_bundle, crs="EPSG:5179")
    assert isinstance(subset, AGSBundle)
    assert set(subset.tables.keys()) == set(KINGDOM_GROUPS)


def test_subset_emission_order(cpt_bundle):
    subset = build_kingdom_subset(cpt_bundle, crs="EPSG:5179")
    assert list(subset.tables.keys()) == list(KINGDOM_GROUPS)


def test_subset_preserves_scpt_data(cpt_bundle):
    subset = build_kingdom_subset(cpt_bundle, crs="EPSG:5179")
    src_scpt = cpt_bundle.tables["SCPT"].iloc[2:]
    new_scpt = subset.tables["SCPT"].iloc[2:]
    assert len(src_scpt) == len(new_scpt)
    assert list(new_scpt["SCPT_DPTH"]) == list(src_scpt["SCPT_DPTH"])


def test_subset_preserves_geol_layers(cpt_bundle):
    subset = build_kingdom_subset(cpt_bundle, crs="EPSG:5179")
    geol = subset.tables["GEOL"].iloc[2:]
    assert len(geol) == 2
    assert geol.iloc[0]["GEOL_LEG"] == "SP"
    assert geol.iloc[1]["GEOL_LEG"] == "CL"


def test_subset_pins_loca_gref(cpt_bundle):
    subset = build_kingdom_subset(cpt_bundle, crs="EPSG:4326")
    loca = subset.tables["LOCA"].iloc[2:]
    assert (loca["LOCA_GREF"] == "EPSG:4326").all()


def test_subset_crs_via_project_meta(cpt_bundle):
    meta = ProjectMeta(crs="EPSG:32652")
    subset = build_kingdom_subset(cpt_bundle, project_meta=meta)
    loca = subset.tables["LOCA"].iloc[2:]
    assert (loca["LOCA_GREF"] == "EPSG:32652").all()


def test_subset_explicit_crs_overrides_project_meta(cpt_bundle):
    meta = ProjectMeta(crs="EPSG:32652")
    subset = build_kingdom_subset(cpt_bundle, project_meta=meta, crs="EPSG:5179")
    loca = subset.tables["LOCA"].iloc[2:]
    assert (loca["LOCA_GREF"] == "EPSG:5179").all()


def test_subset_inherits_existing_loca_gref(cpt_bundle):
    """When neither crs nor project_meta is supplied, the existing
    LOCA_GREF cell is kept (cpt_bundle was written with EPSG:5179)."""
    subset = build_kingdom_subset(cpt_bundle)
    loca = subset.tables["LOCA"].iloc[2:]
    assert (loca["LOCA_GREF"] == "EPSG:5179").all()


# ---------------------------------------------------------------------------
# Excluded groups
# ---------------------------------------------------------------------------


def test_subset_drops_excluded_groups(gi_bundle):
    """SAMP / ISPT in the source must NOT survive the filter."""
    assert "SAMP" in gi_bundle.tables  # sanity — fixture has them
    assert "ISPT" in gi_bundle.tables
    subset = build_kingdom_subset(gi_bundle, crs="EPSG:5179")
    assert "SAMP" not in subset.tables
    assert "ISPT" not in subset.tables


def test_subset_keeps_geol_from_gi_bundle(gi_bundle):
    subset = build_kingdom_subset(gi_bundle, crs="EPSG:5179")
    assert "GEOL" in subset.tables
    assert len(subset.tables["GEOL"].iloc[2:]) == 1


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_subset_requires_loca_group(cpt_bundle):
    cpt_bundle.tables.pop("LOCA")
    with pytest.raises(AgsConvertError, match="LOCA"):
        build_kingdom_subset(cpt_bundle, crs="EPSG:5179")


def test_subset_requires_crs_when_unknown(tmp_path):
    s = _make_cpt_with_strata()
    out = tmp_path / "no_crs.ags"
    write_ags(s, out, project_meta=ProjectMeta(project_id="P01"))
    bundle = load_ags(out)
    with pytest.raises(AgsConvertError, match="LOCA_GREF"):
        build_kingdom_subset(bundle)


def test_subset_unit_dictionary_regenerated(gi_bundle):
    """Units only used by SAMP/ISPT must NOT appear in the subset's
    UNIT dictionary."""
    src_units = set(gi_bundle.tables["UNIT"].iloc[2:]["UNIT_UNIT"])
    subset = build_kingdom_subset(gi_bundle, crs="EPSG:5179")
    new_units = set(subset.tables["UNIT"].iloc[2:]["UNIT_UNIT"])
    # The new dict must be a subset of (or equal to) the original
    assert new_units <= src_units


# ---------------------------------------------------------------------------
# write_kingdom_ags + validator
# ---------------------------------------------------------------------------


def test_write_kingdom_ags_creates_file(tmp_path):
    s = _make_cpt_with_strata()
    out = tmp_path / "k.ags"
    write_kingdom_ags(s, out, project_meta=ProjectMeta(project_id="K01"), crs="EPSG:5179")
    assert out.exists()
    assert out.stat().st_size > 500


def test_write_kingdom_ags_validator_clean(tmp_path):
    """JAKO 1 sounding → Kingdom subset → validate → 0 errors."""
    s = _make_cpt_with_strata()
    out = tmp_path / "k.ags"
    write_kingdom_ags(
        s, out, project_meta=ProjectMeta(project_id="K01"), crs="EPSG:5179"
    )
    errs = validate_file(out)
    fatal = [e for e in errs if e.severity == Severity.ERROR]
    assert fatal == [], f"Kingdom subset has Rule violations: {[str(e) for e in fatal]}"


def test_write_kingdom_ags_groups_match_kingdom_set(tmp_path):
    s = _make_cpt_with_strata()
    out = tmp_path / "k.ags"
    write_kingdom_ags(s, out, project_meta=ProjectMeta(project_id="K01"), crs="EPSG:5179")
    bundle = load_ags(out)
    assert set(bundle.tables.keys()) == set(KINGDOM_GROUPS)


def test_write_kingdom_ags_creates_parent_dirs(tmp_path):
    s = _make_cpt_with_strata()
    out = tmp_path / "deep" / "nested" / "k.ags"
    write_kingdom_ags(s, out, project_meta=ProjectMeta(project_id="K01"), crs="EPSG:5179")
    assert out.exists()
