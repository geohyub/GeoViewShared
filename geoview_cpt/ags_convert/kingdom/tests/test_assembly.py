"""
Tests for Kingdom assembly helper — Phase A-4 Week 18 A4.4.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.ags_convert import ProjectMeta, load_ags
from geoview_cpt.ags_convert.kingdom import (
    KingdomPackage,
    build_kingdom_bundle,
)
from geoview_cpt.ags_convert.validator import Severity, validate_file
from geoview_cpt.model import CPTChannel, CPTHeader, CPTProject, CPTSounding
from geoview_cpt.scpt.first_break_picking import FirstBreakPick


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _sounding(name: str, x: float = 100.0, y: float = 200.0) -> CPTSounding:
    d = np.linspace(0.5, 5.0, 10)
    s = CPTSounding(handle=1, element_tag="", name=name, max_depth_m=5.0)
    s.header = CPTHeader(
        sounding_id=name,
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.8,
        loca_x=x,
        loca_y=y,
        loca_crs="EPSG:5179",
    )
    s.channels = {
        "depth": CPTChannel("depth", "m", d),
        "qc":    CPTChannel("qc", "MPa", np.linspace(1.0, 5.0, 10)),
        "fs":    CPTChannel("fs", "kPa", np.linspace(10.0, 50.0, 10)),
        "u2":    CPTChannel("u2", "kPa", np.linspace(0.0, 20.0, 10)),
    }
    s.derived = {}
    return s


def _picks() -> list[FirstBreakPick]:
    return [
        FirstBreakPick(0, 1.0, 10.0, 10, 0.9, {}),
        FirstBreakPick(1, 2.0, 15.0, 15, 0.8, {}),
        FirstBreakPick(2, 3.0, 21.0, 21, 0.7, {}),
    ]


@pytest.fixture
def project():
    proj = CPTProject(
        source_path=Path("."),
        handle=1,
        name="Test",
        project_id="JAKO-2025",
    )
    proj.soundings = [
        _sounding("CPT01", 100.0, 200.0),
        _sounding("CPT02", 110.0, 210.0),
        _sounding("CPT03", 120.0, 220.0),
    ]
    return proj


@pytest.fixture
def picks_map():
    return {"CPT01": _picks(), "CPT02": _picks()}


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_package_dataclass_fields():
    pkg = KingdomPackage(staging_dir=Path("."), project_id="X", crs="")
    assert pkg.sounding_count == 0
    assert pkg.checkshot_count == 0
    assert pkg.ags_files == []
    assert pkg.manifest_path is None
    assert pkg.readme_path is None


def test_build_kingdom_bundle_creates_subdirs(project, tmp_path):
    staging = tmp_path / "staging"
    build_kingdom_bundle(project, staging, crs="EPSG:5179")
    assert (staging / "AGS").is_dir()
    assert (staging / "LAS").is_dir()
    assert (staging / "checkshot").is_dir()
    assert (staging / "location").is_dir()


def test_build_kingdom_bundle_ags_files_per_sounding(project, tmp_path):
    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(project, staging, crs="EPSG:5179")
    assert len(pkg.ags_files) == 3
    assert pkg.sounding_count == 3
    for p in pkg.ags_files:
        assert p.exists()
        assert p.suffix == ".ags"


def test_build_kingdom_bundle_ags_filename_pattern(project, tmp_path):
    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(project, staging, crs="EPSG:5179")
    names = sorted(p.name for p in pkg.ags_files)
    assert names == [
        "JAKO-2025_CPT01.ags",
        "JAKO-2025_CPT02.ags",
        "JAKO-2025_CPT03.ags",
    ]


def test_build_kingdom_bundle_las_files(project, tmp_path):
    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(project, staging, crs="EPSG:5179")
    assert len(pkg.las_files) == 3
    assert sorted(p.name for p in pkg.las_files) == [
        "CPT01.las", "CPT02.las", "CPT03.las"
    ]


def test_build_kingdom_bundle_checkshot_skip(project, tmp_path, picks_map):
    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(
        project, staging, crs="EPSG:5179", picks_map=picks_map
    )
    assert pkg.checkshot_count == 2
    assert pkg.checkshot_files["CPT01"] is not None
    assert pkg.checkshot_files["CPT02"] is not None
    assert pkg.checkshot_files["CPT03"] is None  # no picks → skipped


def test_build_kingdom_bundle_location_csv(project, tmp_path):
    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(project, staging, crs="EPSG:5179")
    assert pkg.location_csv is not None
    assert pkg.location_csv.exists()
    content = pkg.location_csv.read_text(encoding="utf-8")
    assert content.count("\n") == 4  # header + 3 rows
    assert "CPT01" in content
    assert "CPT02" in content
    assert "CPT03" in content


def test_build_kingdom_bundle_accepts_plain_list(tmp_path):
    soundings = [_sounding("CPT01"), _sounding("CPT02")]
    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(soundings, staging, crs="EPSG:5179")
    assert pkg.sounding_count == 2
    assert pkg.project_id == "GEOVIEW_CPT"  # fallback


def test_build_kingdom_bundle_crs_inheritance_from_header(project, tmp_path):
    """When crs is not supplied anywhere, the first sounding's header CRS wins."""
    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(project, staging)
    assert pkg.crs == "EPSG:5179"


def test_build_kingdom_bundle_crs_project_meta_precedence(project, tmp_path):
    staging = tmp_path / "staging"
    meta = ProjectMeta(crs="EPSG:4326")
    pkg = build_kingdom_bundle(
        project, staging, project_meta=meta
    )
    assert pkg.crs == "EPSG:4326"


def test_build_kingdom_bundle_explicit_crs_wins(project, tmp_path):
    staging = tmp_path / "staging"
    meta = ProjectMeta(crs="EPSG:4326")
    pkg = build_kingdom_bundle(
        project, staging, project_meta=meta, crs="EPSG:32652"
    )
    assert pkg.crs == "EPSG:32652"


def test_build_kingdom_bundle_ags_validator_clean(project, tmp_path):
    """Every ags file emitted must pass the Rule 1-20 validator."""
    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(
        project, staging, project_meta=ProjectMeta(project_id="JAKO-2025"),
        crs="EPSG:5179",
    )
    for ags_path in pkg.ags_files:
        errors = validate_file(ags_path)
        fatal = [e for e in errors if e.severity == Severity.ERROR]
        assert fatal == [], (
            f"{ags_path.name} has Rule violations: {[str(e) for e in fatal]}"
        )


def test_build_kingdom_bundle_sounding_ids_recorded(project, tmp_path):
    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(project, staging, crs="EPSG:5179")
    assert pkg.sounding_ids == ["CPT01", "CPT02", "CPT03"]
