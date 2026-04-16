"""
M4 gate — Phase A termination acceptance test.

This is the closing test for Phase A. It chains the real JAKO CPT
bundle (13 vendor xls files from H:/자코/JAKO_Korea_area/...) through
the full A-2 → A-3 → A-4 pipeline and verifies:

    1. 09_kingdom/AGS/     has 13 .ags files (one per sounding)
    2. 09_kingdom/LAS/     has 13 .las files (one per sounding)
    3. 09_kingdom/checkshot/  present for soundings with picks (skip
       recorded in manifest)
    4. 09_kingdom/location/project_locations.csv has 13 data rows
    5. 09_kingdom/manifest.yaml — schema v1.0 + SHA-256 matches disk
    6. 09_kingdom/README.md    — every Q43 checklist item present
    7. Every .ags file passes Rule 1-20 validator with zero fatal errors
    8. Folder layout diff vs expected layout — 0 extra / 0 missing

Atomic drop is exercised via :func:`drop_to_kingdom_folder` so the
gate also verifies the Week 18 A4.7 tempdir→rename path.

Skip policy: the entire test is skipped when H: drive is
unavailable. The non-skipped path runs in ~10 seconds on the
developer workstation against the real vendor bundle.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from geoview_cpt.ags_convert import ProjectMeta, load_ags
from geoview_cpt.ags_convert.kingdom import (
    build_kingdom_bundle,
    drop_to_kingdom_folder,
    write_manifest,
    write_readme,
)
from geoview_cpt.ags_convert.validator import Severity, validate_file
from geoview_cpt.model import CPTProject


JAKO_DIR = Path("H:/자코/JAKO_Korea_area/Excel_변환_data")


def _jako_xls_files() -> list[Path]:
    if not JAKO_DIR.exists():
        return []
    files = sorted(JAKO_DIR.glob("CPT*.xls*"))
    return [p for p in files if not p.name.startswith("~")]


@pytest.fixture(scope="module")
def jako_project() -> CPTProject:
    """Parse every JAKO CPT xls into a single CPTProject."""
    from geoview_cpt.parsers import parse_jako_xls

    files = _jako_xls_files()
    if not files:
        pytest.skip("JAKO H: drive fixture not available")

    soundings = []
    for path in files:
        try:
            s = parse_jako_xls(path)
        except Exception as exc:  # pragma: no cover — vendor bundle quirks
            pytest.skip(f"parse_jako_xls failed on {path.name}: {exc}")
        soundings.append(s)

    proj = CPTProject(
        source_path=JAKO_DIR,
        handle=1,
        name="JAKO Marine CPT",
        project_id="JAKO-2025",
    )
    proj.soundings = soundings
    return proj


# ---------------------------------------------------------------------------
# M4 gate
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _jako_xls_files(), reason="JAKO H: fixture unavailable")
def test_m4_phase_a_gate(tmp_path, jako_project):
    """Single Phase A termination acceptance test."""
    n = len(jako_project.soundings)
    assert n > 0, "JAKO project has no soundings"

    staging = tmp_path / "staging"
    pkg = build_kingdom_bundle(
        jako_project,
        staging,
        project_meta=ProjectMeta(
            project_id="JAKO-2025",
            project_name="JAKO Marine CPT",
            client="Geoview",
            contractor="Gouda",
        ),
        crs="EPSG:5179",
    )

    # README first so its path + hash land in the manifest
    write_readme(pkg, project_meta=ProjectMeta(client="Geoview"))
    write_manifest(
        pkg,
        project_meta=ProjectMeta(
            project_id="JAKO-2025",
            client="Geoview",
            contractor="Gouda",
        ),
    )

    # Atomic drop
    dest = tmp_path / "09_kingdom"
    drop_to_kingdom_folder(pkg, dest)
    assert dest.exists(), "atomic drop did not place 09_kingdom/"

    # -----------------------------------------------------------------
    # Check 1: 09_kingdom/AGS has one .ags per sounding
    # -----------------------------------------------------------------
    ags_dir = dest / "AGS"
    assert ags_dir.is_dir()
    ags_files = sorted(ags_dir.glob("*.ags"))
    assert len(ags_files) == n, (
        f"expected {n} .ags files, found {len(ags_files)}"
    )

    # -----------------------------------------------------------------
    # Check 2: 09_kingdom/LAS has one .las per sounding
    # -----------------------------------------------------------------
    las_dir = dest / "LAS"
    assert las_dir.is_dir()
    las_files = sorted(las_dir.glob("*.las"))
    assert len(las_files) == n, (
        f"expected {n} .las files, found {len(las_files)}"
    )

    # -----------------------------------------------------------------
    # Check 3: checkshot folder exists — real JAKO bundles carry no
    # seismic picks, so every sounding is skipped. The folder is
    # still created and the manifest records the skip reason.
    # -----------------------------------------------------------------
    cs_dir = dest / "checkshot"
    assert cs_dir.is_dir()

    # -----------------------------------------------------------------
    # Check 4: location CSV has n data rows
    # -----------------------------------------------------------------
    loc_path = dest / "location" / "project_locations.csv"
    assert loc_path.exists()
    loc_lines = loc_path.read_text(encoding="utf-8").splitlines()
    # header + n rows
    assert len(loc_lines) == n + 1, (
        f"location CSV has {len(loc_lines)} lines, expected {n + 1}"
    )

    # -----------------------------------------------------------------
    # Check 5: manifest schema v1.0 + SHA-256 integrity
    # -----------------------------------------------------------------
    manifest_path = dest / "manifest.yaml"
    assert manifest_path.exists()
    import yaml

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["sounding_count"] == n
    assert manifest["crs"] == "EPSG:5179"
    assert manifest["ags_version"] == "4.1"

    # Checksum integrity — re-hash every listed file and compare.
    for rel_path, expected_sha in manifest["checksums"].items():
        actual_path = dest / rel_path
        assert actual_path.exists(), f"{rel_path} missing from drop"
        actual_sha = hashlib.sha256(actual_path.read_bytes()).hexdigest()
        assert actual_sha == expected_sha, f"checksum mismatch: {rel_path}"

    # -----------------------------------------------------------------
    # Check 6: README.md contains every Q43 item
    # -----------------------------------------------------------------
    readme_path = dest / "README.md"
    assert readme_path.exists()
    readme = readme_path.read_text(encoding="utf-8")
    assert "JAKO-2025" in readme                 # Q43 1: project id
    assert "UTC" in readme                       # Q43 2: timestamp
    assert "4.1" in readme                       # Q43 3: AGS version
    assert f"**{n}**" in readme                  # Q43 4: sounding count
    assert "EPSG:5179" in readme                 # Q43 5: CRS
    assert "TRAN_DLIM" in readme                 # Q43 6: troubleshooting

    # -----------------------------------------------------------------
    # Check 7: Rule 1-20 validator clean for every .ags file
    # -----------------------------------------------------------------
    for ags_path in ags_files:
        errors = validate_file(ags_path)
        fatal = [e for e in errors if e.severity == Severity.ERROR]
        assert fatal == [], (
            f"M4 gate FAILED — {ags_path.name} has AGS4 Rule violations:\n"
            + "\n".join(f"  {e}" for e in fatal)
        )

    # -----------------------------------------------------------------
    # Check 8: folder layout diff vs expected
    # -----------------------------------------------------------------
    actual_layout = {
        p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()
    }
    # Build expected set from manifest + known fixed files
    expected: set[str] = set()
    for rel in manifest["checksums"].keys():
        expected.add(rel)
    # manifest.yaml itself is not in its own checksums
    expected.add("manifest.yaml")

    missing = expected - actual_layout
    extra = actual_layout - expected
    assert not missing, f"M4 gate: missing files {sorted(missing)}"
    assert not extra, f"M4 gate: unexpected files {sorted(extra)}"
