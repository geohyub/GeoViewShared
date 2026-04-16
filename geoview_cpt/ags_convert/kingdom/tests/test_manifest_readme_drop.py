"""
Tests for manifest / README / atomic drop — Phase A-4 Week 18 A4.5-A4.7.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.ags_convert import ProjectMeta
from geoview_cpt.ags_convert.kingdom import (
    MANIFEST_SCHEMA_VERSION,
    backup_existing,
    build_kingdom_bundle,
    build_manifest,
    build_readme,
    drop_to_kingdom_folder,
    write_manifest,
    write_readme,
)
from geoview_cpt.ags_convert.wrapper import AgsConvertError
from geoview_cpt.model import CPTChannel, CPTHeader, CPTProject, CPTSounding
from geoview_cpt.scpt.first_break_picking import FirstBreakPick


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _sounding(name: str, x: float = 100.0) -> CPTSounding:
    d = np.linspace(0.5, 5.0, 10)
    s = CPTSounding(handle=1, element_tag="", name=name, max_depth_m=5.0)
    s.header = CPTHeader(
        sounding_id=name,
        cone_base_area_mm2=1000.0,
        cone_area_ratio_a=0.8,
        loca_x=x,
        loca_y=200.0,
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


@pytest.fixture
def package(tmp_path):
    proj = CPTProject(
        source_path=Path("."),
        handle=1,
        name="Test",
        project_id="JAKO-2025",
    )
    proj.soundings = [
        _sounding("CPT01", 100.0),
        _sounding("CPT02", 110.0),
        _sounding("CPT03", 120.0),
    ]
    picks_map = {
        "CPT01": [
            FirstBreakPick(0, 1.0, 10.0, 10, 0.9, {}),
            FirstBreakPick(1, 2.0, 15.0, 15, 0.8, {}),
        ],
    }
    staging = tmp_path / "staging"
    return build_kingdom_bundle(
        proj, staging,
        project_meta=ProjectMeta(project_id="JAKO-2025", client="Geoview"),
        crs="EPSG:5179",
        picks_map=picks_map,
    )


# ---------------------------------------------------------------------------
# build_manifest
# ---------------------------------------------------------------------------


def test_manifest_schema_version():
    assert MANIFEST_SCHEMA_VERSION == "1.0"


def test_manifest_top_level_fields(package):
    pinned = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
    manifest = build_manifest(
        package,
        project_meta=ProjectMeta(project_id="JAKO-2025", client="Geoview"),
        generated_at=pinned,
    )
    assert manifest["schema_version"] == "1.0"
    assert manifest["project_id"] == "JAKO-2025"
    assert manifest["generated_at"] == "2026-04-15T12:00:00Z"
    assert manifest["ags_version"] == "4.1"
    assert manifest["kingdom_subset_version"] == "A4.0"
    assert manifest["crs"] == "EPSG:5179"
    assert manifest["sounding_count"] == 3
    assert manifest["checkshot_count"] == 1
    assert manifest["client"] == "Geoview"


def test_manifest_soundings_list(package):
    manifest = build_manifest(package)
    soundings = manifest["soundings"]
    assert len(soundings) == 3
    assert soundings[0]["id"] == "CPT01"
    assert soundings[0]["ags"] == "AGS/JAKO-2025_CPT01.ags"
    assert soundings[0]["las"] == "LAS/CPT01.las"
    assert soundings[0]["checkshot"] == "checkshot/CPT01.csv"
    assert soundings[0]["reason"] is None


def test_manifest_records_skipped_checkshot(package):
    manifest = build_manifest(package)
    cpt02 = next(s for s in manifest["soundings"] if s["id"] == "CPT02")
    assert cpt02["checkshot"] is None
    assert cpt02["reason"] == "no_seismic_picks"


def test_manifest_location_file_listed(package):
    manifest = build_manifest(package)
    assert manifest["files"]["location"] == "location/project_locations.csv"


def test_manifest_checksums_match_disk(package):
    manifest = build_manifest(package)
    checksums = manifest["checksums"]
    # Every ags file must be in the map, and its hash must match
    # the on-disk SHA-256.
    for ags_path in package.ags_files:
        key = ags_path.relative_to(package.staging_dir).as_posix()
        assert key in checksums
        expected = hashlib.sha256(ags_path.read_bytes()).hexdigest()
        assert checksums[key] == expected


def test_manifest_deterministic_checksum_order(package):
    """Checksum keys must be sorted for reproducibility."""
    manifest = build_manifest(package)
    keys = list(manifest["checksums"].keys())
    assert keys == sorted(keys)


def test_write_manifest_writes_yaml_file(package, tmp_path):
    path = write_manifest(package)
    assert path.exists()
    assert path.name == "manifest.yaml"
    assert package.manifest_path == path
    import yaml

    reloaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert reloaded["project_id"] == "JAKO-2025"


# ---------------------------------------------------------------------------
# build_readme
# ---------------------------------------------------------------------------


def test_readme_contains_q43_checklist(package):
    body = build_readme(
        package,
        project_meta=ProjectMeta(project_id="JAKO-2025", client="Geoview"),
    )
    # Q43 six mandatory items
    assert "JAKO-2025" in body              # 1. project id
    assert "Generated at" in body or "생성 시각" in body  # 2. timestamp
    assert "4.1" in body                    # 3. AGS version
    assert "sounding count" in body.lower() or "sounding" in body.lower()  # 4. counts
    assert "EPSG:5179" in body              # 5. CRS
    assert "TRAN_DLIM" in body              # 6. troubleshooting (Gap #1)


def test_readme_bilingual_korean_english(package):
    body = build_readme(package)
    # Korean headers / English translation presence
    assert "프로젝트" in body
    assert "Project" in body
    assert "폴더 구조" in body
    assert "Folder layout" in body


def test_readme_lists_every_sounding(package):
    body = build_readme(package)
    for sid in ("CPT01", "CPT02", "CPT03"):
        assert sid in body


def test_readme_marks_skipped_checkshot(package):
    body = build_readme(package)
    # One ✅ for CPT01 (has checkshot), ⏭ for CPT02 / CPT03
    assert "⏭" in body
    assert "no_seismic_picks" in body


def test_write_readme_creates_file(package, tmp_path):
    path = write_readme(package)
    assert path.exists()
    assert path.name == "README.md"
    assert package.readme_path == path


def test_manifest_includes_readme_when_written(package):
    write_readme(package)
    manifest = build_manifest(package)
    assert manifest["files"]["readme"] == "README.md"
    # README is in checksums too
    assert "README.md" in manifest["checksums"]


# ---------------------------------------------------------------------------
# drop_helper
# ---------------------------------------------------------------------------


def test_drop_to_fresh_destination(package, tmp_path):
    write_manifest(package)
    write_readme(package)
    dest = tmp_path / "09_kingdom"
    drop_to_kingdom_folder(package, dest)
    assert dest.exists()
    assert (dest / "AGS").is_dir()
    assert (dest / "manifest.yaml").exists()
    assert (dest / "README.md").exists()


def test_drop_backs_up_existing(package, tmp_path):
    write_manifest(package)
    dest = tmp_path / "09_kingdom"
    dest.mkdir()
    (dest / "old.txt").write_text("stale", encoding="utf-8")
    drop_to_kingdom_folder(package, dest)
    assert dest.exists()
    assert not (dest / "old.txt").exists()
    # Backup directory present
    backups = list(tmp_path.glob("09_kingdom.backup.*"))
    assert len(backups) == 1
    assert (backups[0] / "old.txt").exists()


def test_drop_overwrite_without_backup(package, tmp_path):
    dest = tmp_path / "09_kingdom"
    dest.mkdir()
    (dest / "old.txt").write_text("stale", encoding="utf-8")
    drop_to_kingdom_folder(package, dest, backup_existing_dir=False)
    assert not (dest / "old.txt").exists()
    backups = list(tmp_path.glob("09_kingdom.backup.*"))
    assert backups == []


def test_drop_missing_staging_raises(tmp_path):
    from geoview_cpt.ags_convert.kingdom import KingdomPackage

    pkg = KingdomPackage(
        staging_dir=tmp_path / "does_not_exist",
        project_id="X",
        crs="",
    )
    with pytest.raises(AgsConvertError, match="staging"):
        drop_to_kingdom_folder(pkg, tmp_path / "dest")


def test_backup_existing_returns_path(tmp_path):
    target = tmp_path / "x"
    target.mkdir()
    (target / "a.txt").write_text("x", encoding="utf-8")
    backup = backup_existing(target)
    assert backup.exists()
    assert (backup / "a.txt").exists()
    assert not target.exists()
    assert "backup" in backup.name
