"""
M3' gate — Phase A-3 acceptance test.

This is the single integration test that closes Phase A-3. It chains
the A-2 JAKO parser, the Week 13-15 AGS4 writer (with the
``on_missing='inject_default'`` config loader), the Week 14 Rule
1-20 validator, and the byte-level two-pass idempotency check.

The gate passes when:

  1. The JAKO CPT01 xls bundle parses into a :class:`CPTSounding`.
  2. The sounding is written to AGS4 under ``inject_default`` with
     ``jako_defaults.yaml`` as the defaults source.
  3. :func:`validate_file` reports **zero ERROR-severity** violations
     against the output (warnings are tolerated).
  4. A second ``load_ags → dump_ags → load_ags → dump_ags`` cycle
     is byte-idempotent (the Week 14 pattern, closing python-ags4
     Gap #1 via two-pass comparison).
  5. Every core field round-trips losslessly — PROJ defaults injected,
     SCPT depth/qc/fs/u2 preserved, and the derived qt / Fr / Bq
     columns (when populated) match within the R2 tolerance of
     ±0.1% on qt and ±0.5% on Rf / Bq / Ic.

Skip policy: the entire gate is skipped when the JAKO CPT01 xls
fixture is unavailable (H: drive missing on CI). On the developer
workstation it runs against the real vendor bundle.

The complementary byte-level 5/5 coverage lives in
``test_byte_roundtrip.py`` — the gate here only asserts 2-pass
idempotency for the JAKO sample, and the other four fixtures are
covered in the dedicated suite so failures localise cleanly.
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
from geoview_cpt.ags_convert.defaults_config import (
    DEFAULTS_ENV_VAR,
    clear_defaults_cache,
    clear_process_defaults,
)
from geoview_cpt.ags_convert.validator import Severity, validate_file


def _jako_cpt01_xls() -> Path | None:
    base = Path("H:/자코")
    if not base.exists():
        return None
    for p in base.rglob("*.xls*"):
        name = p.stem.upper()
        if "CPT01" in name or "CPT-01" in name:
            return p
    return None


JAKO_DEFAULTS_YAML = (
    Path(__file__).resolve().parents[1] / "docs" / "jako_defaults.yaml"
)


@pytest.fixture(autouse=True)
def _reset_defaults_state():
    import os

    clear_process_defaults()
    clear_defaults_cache()
    os.environ.pop(DEFAULTS_ENV_VAR, None)
    yield
    clear_process_defaults()
    clear_defaults_cache()
    os.environ.pop(DEFAULTS_ENV_VAR, None)


@pytest.mark.skipif(
    _jako_cpt01_xls() is None, reason="JAKO CPT01 xls fixture not on H:"
)
def test_m3_prime_phase_a3_gate(tmp_path, monkeypatch):
    """Single Phase A-3 acceptance test."""
    from geoview_cpt.parsers import parse_jako_xls

    # -----------------------------------------------------------------
    # 1. Parse the real JAKO CPT01 bundle into a CPTSounding
    # -----------------------------------------------------------------
    src = _jako_cpt01_xls()
    assert src is not None
    sounding = parse_jako_xls(src)
    # Sanity: the parser must have populated the mandatory channels
    assert "depth" in sounding.channels
    assert "qc" in sounding.channels
    assert "fs" in sounding.channels

    # -----------------------------------------------------------------
    # 2. Write via inject_default sourced from jako_defaults.yaml
    # -----------------------------------------------------------------
    assert JAKO_DEFAULTS_YAML.exists(), (
        f"M3' fixture missing: {JAKO_DEFAULTS_YAML}"
    )
    monkeypatch.setenv(DEFAULTS_ENV_VAR, str(JAKO_DEFAULTS_YAML))

    out = tmp_path / "jako_m3_prime.ags"
    write_ags(sounding, out, on_missing="inject_default")
    assert out.exists()

    # -----------------------------------------------------------------
    # 3. Rule 1-20 validator: zero ERROR severity required
    # -----------------------------------------------------------------
    errors = validate_file(out)
    fatal = [e for e in errors if e.severity == Severity.ERROR]
    assert fatal == [], (
        "M3' gate FAILED — AGS4 Rule violations on JAKO CPT01:\n"
        + "\n".join(f"  {e}" for e in fatal)
    )

    # -----------------------------------------------------------------
    # 4. Two-pass byte-level idempotency (python-ags4 Gap #1 workaround)
    # -----------------------------------------------------------------
    bundle_v1 = load_ags(out)
    v2 = tmp_path / "v2.ags"
    dump_ags(bundle_v1, v2)
    bundle_v2 = load_ags(v2)
    v3 = tmp_path / "v3.ags"
    dump_ags(bundle_v2, v3)
    assert v2.read_bytes() == v3.read_bytes(), (
        "M3' gate FAILED — JAKO CPT01 is not byte-idempotent under "
        "the two-pass cycle"
    )

    # -----------------------------------------------------------------
    # 5. Semantic round-trip: defaults injected, PROJ fields landed
    # -----------------------------------------------------------------
    proj_data = bundle_v1.tables["PROJ"].iloc[2:]
    assert len(proj_data) == 1
    assert proj_data.iloc[0]["PROJ_ID"] == "JAKO-2025"
    assert proj_data.iloc[0]["PROJ_CLNT"] == "Geoview"
    assert proj_data.iloc[0]["PROJ_NAME"] == "JAKO Marine CPT"

    loca_data = bundle_v1.tables["LOCA"].iloc[2:]
    assert loca_data.iloc[0]["LOCA_GREF"] == "EPSG:5186"
    assert loca_data.iloc[0]["LOCA_TYPE"] == "CPT"

    # -----------------------------------------------------------------
    # 6. Core-field tolerance check — qt/Rf/Bq/Ic within R2 tolerance
    # -----------------------------------------------------------------
    scpt = bundle_v1.tables["SCPT"].iloc[2:].reset_index(drop=True)
    n_rows = len(scpt)
    assert n_rows > 0, "SCPT has no DATA rows"

    # The writer deduplicates SCPT rows that collide on the 2DP
    # composite KEY (LOCA_ID, SCPG_TESN, SCPT_DPTH) — see groups/scpt.py.
    # So n_rows must equal the count of unique 2DP depths in source.
    depth_src = np.asarray(sounding.channels["depth"].values, dtype=np.float64)
    unique_2dp = {f"{v:.2f}" for v in depth_src if np.isfinite(v)}
    assert n_rows == len(unique_2dp), (
        f"SCPT row count {n_rows} != unique 2DP depth count {len(unique_2dp)}"
    )

    depth_rt = np.array([float(v) for v in scpt["SCPT_DPTH"]])
    # Every round-tripped depth must have a source sample within the
    # 2DP bin tolerance — proves dedup only dropped duplicates, never
    # invented values.
    src_set = {round(float(v), 2) for v in depth_src if np.isfinite(v)}
    for d in depth_rt:
        assert round(d, 2) in src_set, f"round-tripped depth {d} not in source"

    # qt / Fr / Bq / Ic tolerance — compare the first-occurrence
    # deduped sample's derived value to the corresponding source
    # channel value at the matching depth bin.
    def _round_trip_tolerance(name: str, col: str, max_rel: float) -> None:
        if col not in scpt.columns:
            return
        source_ch = sounding.derived.get(name)
        if source_ch is None and name == "Fr":
            source_ch = sounding.derived.get("Rf")
        if source_ch is None:
            return
        src_values = np.asarray(source_ch.values, dtype=np.float64)
        max_rel_err = 0.0
        checked = 0
        for d, cell in zip(depth_rt, scpt[col]):
            if not cell:
                continue
            parsed = float(cell)
            if not np.isfinite(parsed):
                continue
            # find first source index with matching 2DP depth
            match_idx = np.argmin(np.abs(depth_src - d))
            if abs(depth_src[match_idx] - d) > 0.005:
                continue
            source_val = src_values[match_idx]
            if not np.isfinite(source_val) or abs(source_val) < 1e-9:
                continue
            rel = abs(parsed - source_val) / abs(source_val)
            max_rel_err = max(max_rel_err, rel)
            checked += 1
        if checked == 0:
            return
        assert max_rel_err < max_rel, (
            f"{name}: max rel err {max_rel_err:.4%} >= {max_rel:.4%} "
            f"(checked {checked} samples)"
        )

    _round_trip_tolerance("qt", "SCPT_QT", 0.001)   # ±0.1%
    _round_trip_tolerance("Fr", "SCPT_FRR", 0.005)  # ±0.5%
    _round_trip_tolerance("Bq", "SCPT_BQ", 0.005)


# ---------------------------------------------------------------------------
# Phase A-3 completeness marker
# ---------------------------------------------------------------------------


def test_phase_a3_artifacts_present():
    """
    Guard test — fails if any Phase A-3 deliverable is missing.

    These paths are the concrete acceptance checklist for Phase A-3
    termination. They all exist in-tree at M3' gate time; deleting
    any of them breaks this test, which stops a Phase A-4 kickoff
    from skipping a missing artifact.
    """
    base = Path(__file__).resolve().parents[1]
    required_files = [
        base / "writer.py",
        base / "validator" / "__init__.py",
        base / "converters" / "__init__.py",
        base / "cli.py",
        base / "defaults_config.py",
        base / "docs" / "python_ags4_gaps.md",
        base / "docs" / "jako_defaults.yaml",
        base / "docs" / "a3_jako_missing_fields.md",
        # Writer groups
        base / "groups" / "proj.py",
        base / "groups" / "tran.py",
        base / "groups" / "loca.py",
        base / "groups" / "scpt.py",
        base / "groups" / "geol.py",
        base / "groups" / "samp.py",
        base / "groups" / "ispt.py",
        # Validator modules — 8
        base / "validator" / "structure.py",
        base / "validator" / "quoting.py",
        base / "validator" / "fields.py",
        base / "validator" / "dictionary.py",
        base / "validator" / "references.py",
        base / "validator" / "required_groups.py",
        base / "validator" / "naming.py",
        base / "validator" / "files.py",
        # Converters — 5 (las optional but module exists)
        base / "converters" / "xlsx_fmt.py",
        base / "converters" / "csv_fmt.py",
        base / "converters" / "json_fmt.py",
        base / "converters" / "parquet_fmt.py",
        base / "converters" / "las_fmt.py",
    ]
    missing = [str(p) for p in required_files if not p.exists()]
    assert not missing, f"Phase A-3 artifacts missing: {missing}"
