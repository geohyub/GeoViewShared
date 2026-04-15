"""
Tests for the Kingdom checkshot CSV writer — Phase A-4 Week 17 A4.2.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from geoview_cpt.ags_convert.kingdom import (
    CHECKSHOT_COLUMNS,
    SCPTSoundingPicks,
    build_checkshot_csv,
    build_checkshot_directory,
)
from geoview_cpt.scpt.first_break_picking import FirstBreakPick


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _picks() -> list[FirstBreakPick]:
    """Three monotonic depth/time picks with descending confidence."""
    return [
        FirstBreakPick(trace_index=0, depth_m=1.0, time_ms=10.0,
                       sample_index=10, confidence=0.95, trace_info={}),
        FirstBreakPick(trace_index=1, depth_m=2.0, time_ms=15.0,
                       sample_index=15, confidence=0.78, trace_info={}),
        FirstBreakPick(trace_index=2, depth_m=3.0, time_ms=21.0,
                       sample_index=21, confidence=0.50, trace_info={}),
        FirstBreakPick(trace_index=3, depth_m=4.0, time_ms=28.0,
                       sample_index=28, confidence=0.20, trace_info={}),
    ]


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8") as fh:
        # Skip leading comment lines
        lines = [ln for ln in fh if not ln.startswith("#")]
    reader = csv.reader(lines)
    rows = list(reader)
    return rows[0], rows[1:]


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def test_checkshot_columns_match_kingdom_schema():
    assert CHECKSHOT_COLUMNS == (
        "Depth_m",
        "TWT_ms",
        "Interval_Vs_m_s",
        "Average_Vs_m_s",
        "Source_Offset_m",
        "Quality_Flag",
    )


# ---------------------------------------------------------------------------
# build_checkshot_csv
# ---------------------------------------------------------------------------


def test_checkshot_writes_csv_with_header(tmp_path):
    rec = SCPTSoundingPicks(loca_id="CPT01", picks=_picks(), crs="EPSG:5179")
    out = tmp_path / "CPT01.csv"
    result = build_checkshot_csv(rec, out)
    assert result == out
    assert out.exists()
    header, rows = _read_csv(out)
    assert header == list(CHECKSHOT_COLUMNS)
    assert len(rows) == 4


def test_checkshot_crs_comment_emitted(tmp_path):
    rec = SCPTSoundingPicks("CPT01", _picks(), crs="EPSG:5179")
    out = tmp_path / "x.csv"
    build_checkshot_csv(rec, out)
    first_line = out.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "# CRS: EPSG:5179"


def test_checkshot_no_crs_skips_comment(tmp_path):
    rec = SCPTSoundingPicks("CPT01", _picks())
    out = tmp_path / "x.csv"
    build_checkshot_csv(rec, out)
    first_line = out.read_text(encoding="utf-8").splitlines()[0]
    assert not first_line.startswith("#")


def test_checkshot_first_row_has_blank_velocities(tmp_path):
    rec = SCPTSoundingPicks("CPT01", _picks(), crs="EPSG:5179")
    out = tmp_path / "x.csv"
    build_checkshot_csv(rec, out)
    _, rows = _read_csv(out)
    # First row: no previous pick → interval / average blank
    assert rows[0][2] == ""
    assert rows[0][3] == ""


def test_checkshot_interval_velocity_uses_a2_helper(tmp_path):
    """Pick0 (1.0m, 10ms) → Pick1 (2.0m, 15ms) → 1.0 / (5e-3) = 200 m/s."""
    rec = SCPTSoundingPicks("CPT01", _picks(), crs="EPSG:5179")
    out = tmp_path / "x.csv"
    build_checkshot_csv(rec, out)
    _, rows = _read_csv(out)
    assert rows[1][2] == "200.0"


def test_checkshot_quality_flag_grading(tmp_path):
    rec = SCPTSoundingPicks("CPT01", _picks(), crs="EPSG:5179")
    out = tmp_path / "x.csv"
    build_checkshot_csv(rec, out)
    _, rows = _read_csv(out)
    qualities = [r[5] for r in rows]
    # confidences: 0.95→A, 0.78→B, 0.50→C, 0.20→D
    assert qualities == ["A", "B", "C", "D"]


def test_checkshot_source_offset_switches_to_pseudo(tmp_path):
    """Non-zero source offset should change the interval velocity (pseudo formula)."""
    base = SCPTSoundingPicks("CPT01", _picks(), crs="EPSG:5179")
    offset = SCPTSoundingPicks(
        "CPT01", _picks(), crs="EPSG:5179", source_offset_m=2.0
    )
    p1 = tmp_path / "base.csv"
    p2 = tmp_path / "offset.csv"
    build_checkshot_csv(base, p1)
    build_checkshot_csv(offset, p2)
    _, base_rows = _read_csv(p1)
    _, off_rows = _read_csv(p2)
    # Same depth/twt → vertical-assumption v differs from straight-ray v
    assert base_rows[1][2] != off_rows[1][2]
    # Source offset column reflects the parameter
    assert off_rows[0][4] == "2.0"


def test_checkshot_skips_when_no_picks(tmp_path):
    rec = SCPTSoundingPicks("CPT01", [], crs="EPSG:5179")
    out = tmp_path / "empty.csv"
    result = build_checkshot_csv(rec, out)
    assert result is None
    assert not out.exists()


def test_checkshot_creates_parent_dirs(tmp_path):
    rec = SCPTSoundingPicks("CPT01", _picks())
    out = tmp_path / "deep" / "nested" / "x.csv"
    build_checkshot_csv(rec, out)
    assert out.exists()


# ---------------------------------------------------------------------------
# build_checkshot_directory
# ---------------------------------------------------------------------------


def test_checkshot_directory_writes_each_sounding(tmp_path):
    records = [
        SCPTSoundingPicks("CPT01", _picks()),
        SCPTSoundingPicks("CPT02", _picks()),
        SCPTSoundingPicks("CPT03", []),  # skipped
    ]
    target = tmp_path / "checkshot"
    result = build_checkshot_directory(records, target)
    assert result["CPT01"] == target / "CPT01.csv"
    assert result["CPT02"] == target / "CPT02.csv"
    assert result["CPT03"] is None
    assert (target / "CPT01.csv").exists()
    assert (target / "CPT02.csv").exists()
    assert not (target / "CPT03.csv").exists()
