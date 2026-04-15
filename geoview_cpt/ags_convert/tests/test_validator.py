"""
Tests for the Rule 1–20 validator — Phase A-3 Week 14 A3.3.

Tests fall into two groups:

- **rule unit tests** — hand-built synthetic bundles and raw byte
  strings that exercise one rule at a time (happy + error paths).
- **integration tests** — run ``validate_file`` against the output
  of our Week 13 writer and assert that the rules we expect to fire
  do fire, while rules unrelated to known writer gaps stay silent.

The writer-gap expectations are recorded explicitly so Week 15
writer refinement can flip them as the gaps close.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from geoview_cpt.ags_convert import ProjectMeta, write_ags, write_gi_ags
from geoview_cpt.ags_convert.validator import (
    Severity,
    ValidationError,
    check_rule_1,
    check_rule_2,
    check_rule_2a,
    check_rule_3,
    check_rule_5,
    check_rule_6,
    check_rule_7,
    check_rule_8,
    check_rule_9,
    check_rule_10,
    check_rule_10a,
    check_rule_10b,
    check_rule_10c,
    check_rule_11,
    check_rule_12,
    check_rule_13,
    check_rule_14,
    check_rule_15,
    check_rule_16,
    check_rule_17,
    check_rule_18,
    check_rule_19,
    check_rule_19a,
    check_rule_20,
    validate_bundle,
    validate_file,
)
from geoview_cpt.ags_convert.wrapper import AGSBundle
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding
from geoview_gi.minimal_model import Borehole, LabSample, SPTTest, StratumLayer


# ---------------------------------------------------------------------------
# Fixtures — hand-built bundle for rule unit tests
# ---------------------------------------------------------------------------


def _minimal_bundle() -> AGSBundle:
    """Hand-built bundle that satisfies every rule under Week 14 coverage."""
    proj = pd.DataFrame(
        [
            {"HEADING": "UNIT", "PROJ_ID": "", "PROJ_NAME": ""},
            {"HEADING": "TYPE", "PROJ_ID": "ID", "PROJ_NAME": "X"},
            {"HEADING": "DATA", "PROJ_ID": "P01", "PROJ_NAME": "JAKO"},
        ]
    )
    tran = pd.DataFrame(
        [
            {"HEADING": "UNIT", "TRAN_ISNO": "", "TRAN_DATE": "yyyy-mm-dd"},
            {"HEADING": "TYPE", "TRAN_ISNO": "X", "TRAN_DATE": "DT"},
            {"HEADING": "DATA", "TRAN_ISNO": "1", "TRAN_DATE": "2025-10-01"},
        ]
    )
    unit = pd.DataFrame(
        [
            {"HEADING": "UNIT", "UNIT_UNIT": "", "UNIT_DESC": ""},
            {"HEADING": "TYPE", "UNIT_UNIT": "X", "UNIT_DESC": "X"},
            {"HEADING": "DATA", "UNIT_UNIT": "m", "UNIT_DESC": "metre"},
            {"HEADING": "DATA", "UNIT_UNIT": "yyyy-mm-dd", "UNIT_DESC": "date"},
        ]
    )
    type_g = pd.DataFrame(
        [
            {"HEADING": "UNIT", "TYPE_TYPE": "", "TYPE_DESC": ""},
            {"HEADING": "TYPE", "TYPE_TYPE": "X", "TYPE_DESC": "X"},
            {"HEADING": "DATA", "TYPE_TYPE": "ID", "TYPE_DESC": "Id"},
            {"HEADING": "DATA", "TYPE_TYPE": "X", "TYPE_DESC": "Text"},
            {"HEADING": "DATA", "TYPE_TYPE": "DT", "TYPE_DESC": "Date"},
            {"HEADING": "DATA", "TYPE_TYPE": "2DP", "TYPE_DESC": "2DP"},
        ]
    )
    loca = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": ""},
            {"HEADING": "TYPE", "LOCA_ID": "ID"},
            {"HEADING": "DATA", "LOCA_ID": "BH-01"},
            {"HEADING": "DATA", "LOCA_ID": "BH-02"},
        ]
    )
    tables = {
        "PROJ": proj,
        "TRAN": tran,
        "UNIT": unit,
        "TYPE": type_g,
        "LOCA": loca,
    }
    for df in tables.values():
        for col in df.columns:
            df[col] = df[col].astype(str)
    headings = {g: list(df.columns) for g, df in tables.items()}
    return AGSBundle(tables=tables, headings=headings)


# ---------------------------------------------------------------------------
# Structure rules (1 / 2 / 2a / 3)
# ---------------------------------------------------------------------------


def test_rule_1_clean():
    assert check_rule_1(b'"GROUP","PROJ"\r\n') == []


def test_rule_1_bom_detected():
    errors = check_rule_1(b"\xef\xbb\xbf\"GROUP\",\"PROJ\"\r\n")
    assert len(errors) == 1
    assert errors[0].rule == "1"


def test_rule_1_invalid_utf8():
    errors = check_rule_1(b"\xff\xfe invalid")
    assert any("UTF-8" in e.message for e in errors)


def test_rule_2_clean_crlf():
    assert check_rule_2(b'"GROUP","PROJ"\r\n"HEADING","PROJ_ID"\r\n') == []


def test_rule_2_bare_lf_detected():
    errors = check_rule_2(b'"GROUP","PROJ"\n"HEADING","PROJ_ID"\r\n')
    assert errors and errors[0].rule == "2"


def test_rule_2a_blank_line_between_groups():
    raw = (
        b'"GROUP","PROJ"\r\n'
        b'"HEADING","PROJ_ID"\r\n'
        b'"UNIT",""\r\n"TYPE","ID"\r\n"DATA","P01"\r\n'
        b'\r\n'
        b'"GROUP","TRAN"\r\n'
    )
    assert check_rule_2a(raw) == []


def test_rule_2a_missing_blank_line():
    raw = (
        b'"GROUP","PROJ"\r\n'
        b'"HEADING","PROJ_ID"\r\n'
        b'"UNIT",""\r\n"TYPE","ID"\r\n"DATA","P01"\r\n'
        b'"GROUP","TRAN"\r\n'
    )
    errors = check_rule_2a(raw)
    assert errors and errors[0].rule == "2a"


def test_rule_3_known_record_types():
    raw = b'"GROUP","PROJ"\r\n"HEADING","PROJ_ID"\r\n"DATA","P01"\r\n'
    assert check_rule_3(raw) == []


def test_rule_3_unknown_record_type():
    raw = b'"BOGUS","PROJ"\r\n'
    errors = check_rule_3(raw)
    assert errors and errors[0].rule == "3"


# ---------------------------------------------------------------------------
# Quoting rules (5 / 6)
# ---------------------------------------------------------------------------


def test_rule_5_clean():
    raw = b'"GROUP","PROJ"\r\n"HEADING","PROJ_ID"\r\n"DATA","P01"\r\n'
    assert check_rule_5(raw) == []


def test_rule_5_unbalanced_quotes():
    raw = b'"GROUP","PROJ\r\n'  # missing closing quote
    errors = check_rule_5(raw)
    assert errors and errors[0].rule == "5"


def test_rule_6_field_counts_match():
    raw = (
        b'"GROUP","PROJ"\r\n'
        b'"HEADING","PROJ_ID","PROJ_NAME"\r\n'
        b'"UNIT","",""\r\n'
        b'"TYPE","ID","X"\r\n'
        b'"DATA","P01","JAKO"\r\n'
    )
    assert check_rule_6(raw) == []


def test_rule_6_field_count_mismatch():
    raw = (
        b'"GROUP","PROJ"\r\n'
        b'"HEADING","PROJ_ID","PROJ_NAME"\r\n'
        b'"DATA","P01"\r\n'
    )
    errors = check_rule_6(raw)
    assert any(e.rule == "6" for e in errors)


# ---------------------------------------------------------------------------
# Fields rules (7 / 8 / 12)
# ---------------------------------------------------------------------------


def test_rule_7_invariant_preserved():
    bundle = _minimal_bundle()
    assert check_rule_7(bundle) == []


def test_rule_8_numeric_check_green():
    bundle = _minimal_bundle()
    assert check_rule_8(bundle) == []


def test_rule_8_numeric_check_red():
    bundle = _minimal_bundle()
    bad_df = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": "", "LOCA_NATE": "m"},
            {"HEADING": "TYPE", "LOCA_ID": "ID", "LOCA_NATE": "2DP"},
            {"HEADING": "DATA", "LOCA_ID": "BH-1", "LOCA_NATE": "not-a-number"},
        ]
    )
    bundle.tables["LOCA"] = bad_df.astype(str)
    errors = check_rule_8(bundle)
    assert any(e.heading == "LOCA_NATE" and e.rule == "8" for e in errors)


def test_rule_12_unit_used_but_not_declared():
    bundle = _minimal_bundle()
    loca = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": "", "LOCA_NATE": "furlong"},
            {"HEADING": "TYPE", "LOCA_ID": "ID", "LOCA_NATE": "2DP"},
            {"HEADING": "DATA", "LOCA_ID": "BH-1", "LOCA_NATE": "123"},
        ]
    ).astype(str)
    bundle.tables["LOCA"] = loca
    errors = check_rule_12(bundle)
    assert any(e.heading == "LOCA_NATE" and "furlong" in e.message for e in errors)


# ---------------------------------------------------------------------------
# Dictionary rules (9 / 10 / 10a / 10b)
# ---------------------------------------------------------------------------


def test_rule_9_known_headings_clean():
    bundle = _minimal_bundle()
    assert check_rule_9(bundle) == []


def test_rule_9_unknown_heading_flagged():
    bundle = _minimal_bundle()
    loca = bundle.tables["LOCA"].copy()
    loca["LOCA_BOGUS"] = ["", "X", "a", "b"]
    bundle.tables["LOCA"] = loca.astype(str)
    errors = check_rule_9(bundle)
    assert any(e.heading == "LOCA_BOGUS" for e in errors)


def test_rule_10_missing_key_column():
    bundle = _minimal_bundle()
    # Remove LOCA_ID from LOCA — KEY col missing
    bad = bundle.tables["LOCA"].drop(columns=["LOCA_ID"])
    bad["DUMMY"] = ["", "X", "a", "b"]
    bundle.tables["LOCA"] = bad.astype(str)
    errors = check_rule_10(bundle)
    assert any(e.heading == "LOCA_ID" for e in errors)


def test_rule_10a_composite_key_duplicate():
    bundle = _minimal_bundle()
    loca = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": ""},
            {"HEADING": "TYPE", "LOCA_ID": "ID"},
            {"HEADING": "DATA", "LOCA_ID": "BH-1"},
            {"HEADING": "DATA", "LOCA_ID": "BH-1"},  # duplicate
        ]
    ).astype(str)
    bundle.tables["LOCA"] = loca
    errors = check_rule_10a(bundle)
    assert any(e.rule == "10a" for e in errors)


def test_rule_10b_blank_key_flagged():
    bundle = _minimal_bundle()
    loca = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": ""},
            {"HEADING": "TYPE", "LOCA_ID": "ID"},
            {"HEADING": "DATA", "LOCA_ID": ""},
        ]
    ).astype(str)
    bundle.tables["LOCA"] = loca
    errors = check_rule_10b(bundle)
    assert any(e.rule == "10b" and e.heading == "LOCA_ID" for e in errors)


# ---------------------------------------------------------------------------
# References rules (10c / 11)
# ---------------------------------------------------------------------------


def test_rule_10c_orphan_reference():
    bundle = _minimal_bundle()
    # Add a GEOL row pointing at a LOCA_ID that does not exist
    geol = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": "", "GEOL_TOP": "m", "GEOL_BASE": "m"},
            {"HEADING": "TYPE", "LOCA_ID": "ID", "GEOL_TOP": "2DP", "GEOL_BASE": "2DP"},
            {"HEADING": "DATA", "LOCA_ID": "GHOST", "GEOL_TOP": "0.00", "GEOL_BASE": "1.00"},
        ]
    ).astype(str)
    bundle.tables["GEOL"] = geol
    errors = check_rule_10c(bundle)
    assert any(e.rule == "10c" and "GHOST" in e.message for e in errors)


def test_rule_10c_valid_reference():
    bundle = _minimal_bundle()
    geol = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": "", "GEOL_TOP": "m", "GEOL_BASE": "m"},
            {"HEADING": "TYPE", "LOCA_ID": "ID", "GEOL_TOP": "2DP", "GEOL_BASE": "2DP"},
            {"HEADING": "DATA", "LOCA_ID": "BH-01", "GEOL_TOP": "0.00", "GEOL_BASE": "1.00"},
        ]
    ).astype(str)
    bundle.tables["GEOL"] = geol
    assert check_rule_10c(bundle) == []


def test_rule_11_missing_parent_reference_column():
    bundle = _minimal_bundle()
    # GEOL without LOCA_ID
    geol = pd.DataFrame(
        [
            {"HEADING": "UNIT", "GEOL_TOP": "m"},
            {"HEADING": "TYPE", "GEOL_TOP": "2DP"},
            {"HEADING": "DATA", "GEOL_TOP": "0.00"},
        ]
    ).astype(str)
    bundle.tables["GEOL"] = geol
    errors = check_rule_11(bundle)
    assert any(e.rule == "11" and e.group == "GEOL" for e in errors)


# ---------------------------------------------------------------------------
# Required-group rules (13 – 18)
# ---------------------------------------------------------------------------


def test_rule_13_proj_missing():
    bundle = _minimal_bundle()
    del bundle.tables["PROJ"]
    errors = check_rule_13(bundle)
    assert any(e.rule == "13" for e in errors)


def test_rule_13_proj_empty():
    bundle = _minimal_bundle()
    proj_empty = pd.DataFrame(
        [
            {"HEADING": "UNIT", "PROJ_ID": ""},
            {"HEADING": "TYPE", "PROJ_ID": "ID"},
        ]
    ).astype(str)
    bundle.tables["PROJ"] = proj_empty
    errors = check_rule_13(bundle)
    assert any(e.rule == "13" for e in errors)


def test_rule_14_tran_missing():
    bundle = _minimal_bundle()
    del bundle.tables["TRAN"]
    errors = check_rule_14(bundle)
    assert errors and errors[0].rule == "14"


def test_rules_15_16_clean():
    bundle = _minimal_bundle()
    assert check_rule_15(bundle) == []
    assert check_rule_16(bundle) == []


def test_rule_17_undeclared_type_code():
    bundle = _minimal_bundle()
    loca = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": "", "LOCA_NATE": "m"},
            {"HEADING": "TYPE", "LOCA_ID": "ID", "LOCA_NATE": "BOGUS"},
            {"HEADING": "DATA", "LOCA_ID": "BH-1", "LOCA_NATE": "0"},
        ]
    ).astype(str)
    bundle.tables["LOCA"] = loca
    errors = check_rule_17(bundle)
    assert any(e.heading == "LOCA_NATE" and e.rule == "17" for e in errors)


def test_rule_18_dict_empty_warning():
    bundle = _minimal_bundle()
    bundle.tables["DICT"] = pd.DataFrame(
        [
            {"HEADING": "UNIT", "DICT_GRP": "", "DICT_HDNG": ""},
            {"HEADING": "TYPE", "DICT_GRP": "X", "DICT_HDNG": "X"},
        ]
    ).astype(str)
    errors = check_rule_18(bundle)
    assert any(e.rule == "18" and e.severity == Severity.WARNING for e in errors)


# ---------------------------------------------------------------------------
# Naming rules (19 / 19a)
# ---------------------------------------------------------------------------


def test_rule_19_standard_groups_clean():
    bundle = _minimal_bundle()
    assert check_rule_19(bundle) == []


def test_rule_19_invalid_group_name():
    bundle = _minimal_bundle()
    bundle.tables["bad_name"] = bundle.tables["LOCA"].copy()
    errors = check_rule_19(bundle)
    assert any(e.group == "bad_name" for e in errors)


def test_rule_19a_headings_match_pattern():
    bundle = _minimal_bundle()
    assert check_rule_19a(bundle) == []


def test_rule_19a_lowercase_heading_fails():
    bundle = _minimal_bundle()
    bad = bundle.tables["LOCA"].copy()
    bad.columns = ["HEADING", "loca_id"]
    bundle.tables["LOCA"] = bad
    errors = check_rule_19a(bundle)
    assert any(e.heading == "loca_id" for e in errors)


# ---------------------------------------------------------------------------
# Files rule (20)
# ---------------------------------------------------------------------------


def test_rule_20_missing_file(tmp_path):
    df = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": "", "FILE_FSET": ""},
            {"HEADING": "TYPE", "LOCA_ID": "ID", "FILE_FSET": "X"},
            {"HEADING": "DATA", "LOCA_ID": "BH-1", "FILE_FSET": "no_such_file.pdf"},
        ]
    ).astype(str)
    bundle = AGSBundle(tables={"LOCA": df}, headings={"LOCA": list(df.columns)})
    errors = check_rule_20(bundle, base_dir=tmp_path)
    assert errors and errors[0].rule == "20"


def test_rule_20_file_present(tmp_path):
    (tmp_path / "log.pdf").write_bytes(b"x")
    df = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": "", "FILE_FSET": ""},
            {"HEADING": "TYPE", "LOCA_ID": "ID", "FILE_FSET": "X"},
            {"HEADING": "DATA", "LOCA_ID": "BH-1", "FILE_FSET": "log.pdf"},
        ]
    ).astype(str)
    bundle = AGSBundle(tables={"LOCA": df}, headings={"LOCA": list(df.columns)})
    assert check_rule_20(bundle, base_dir=tmp_path) == []


# ---------------------------------------------------------------------------
# End-to-end validate_file and validate_bundle
# ---------------------------------------------------------------------------


def test_validate_bundle_clean():
    bundle = _minimal_bundle()
    errors = validate_bundle(bundle)
    errs_by_rule = sorted({e.rule for e in errors})
    assert errs_by_rule == [], f"unexpected errors: {errors}"


def test_validate_file_end_to_end_clean_after_w1_w4(tmp_path):
    """
    After the Week 15 W1-W4 writer refinement the writer's output
    must be Rule 1-20 clean (errors == 0). Warnings are tolerated.
    """
    d = np.linspace(0.5, 2.0, 4)
    s = CPTSounding(handle=1, element_tag="", name="CPT01", max_depth_m=2.0)
    s.header = CPTHeader(
        sounding_id="CPT01", cone_base_area_mm2=1000.0, cone_area_ratio_a=0.8
    )
    s.channels = {
        "depth": CPTChannel("depth", "m", d),
        "qc":    CPTChannel("qc", "MPa", np.array([1.0, 2.0, 3.0, 4.0])),
        "fs":    CPTChannel("fs", "kPa", np.array([10.0, 20.0, 30.0, 40.0])),
        "u2":    CPTChannel("u2", "kPa", np.array([0.0, 5.0, 10.0, 15.0])),
    }
    s.derived = {}

    out = tmp_path / "cpt.ags"
    write_ags(s, out, project_meta=ProjectMeta(project_id="P01"))
    errors = validate_file(out)

    fatal = [e for e in errors if e.severity == Severity.ERROR]
    assert fatal == [], f"writer produced AGS4 Rule violations: {[str(e) for e in fatal]}"


def test_validate_file_gi_end_to_end(tmp_path):
    """GI bundle should pass the structural + required-group rules."""
    bh = Borehole(
        loca_id="BH-01",
        client="Geoview",
        easting_m=100.0,
        northing_m=200.0,
        crs="EPSG:5186",
        ground_level_m=2.5,
        final_depth_m=10.0,
        start_date=date(2025, 10, 1),
        method="Rotary Core",
    )
    bh.add_stratum(StratumLayer(top_m=0.0, base_m=3.0, description="sand", legend_code="SP"))
    bh.add_stratum(StratumLayer(top_m=3.0, base_m=10.0, description="clay", legend_code="CL"))
    bh.add_spt(SPTTest(top_m=2.0, main_blows=15, n_value=15))

    out = tmp_path / "gi.ags"
    write_gi_ags(bh, out, project_meta=ProjectMeta(project_id="P01"))
    errors = validate_file(out)
    rules = {e.rule for e in errors}
    # Structural rules must be clean
    assert "1" not in rules
    assert "2" not in rules
    assert "5" not in rules
    assert "6" not in rules
    # Rule 10c: all GEOL and ISPT rows reference an existing LOCA_ID
    assert "10c" not in rules


def test_rule_10c_catches_geol_orphan_via_full_validate():
    """Explicit integration check — GEOL with unknown LOCA_ID fails 10c."""
    bundle = _minimal_bundle()
    geol = pd.DataFrame(
        [
            {"HEADING": "UNIT", "LOCA_ID": "", "GEOL_TOP": "m", "GEOL_BASE": "m"},
            {"HEADING": "TYPE", "LOCA_ID": "ID", "GEOL_TOP": "2DP", "GEOL_BASE": "2DP"},
            {"HEADING": "DATA", "LOCA_ID": "UNKNOWN", "GEOL_TOP": "0.00", "GEOL_BASE": "1.00"},
        ]
    ).astype(str)
    bundle.tables["GEOL"] = geol
    errors = validate_bundle(bundle)
    assert any(e.rule == "10c" for e in errors)
