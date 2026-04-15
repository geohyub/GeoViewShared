"""Tests for geoview_cpt.ags_convert.jako_audit — Phase A-3 Week 12."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from geoview_cpt.ags_convert import (
    AGS4_CORE_GROUPS,
    AuditReport,
    audit_missing_fields,
)
from geoview_cpt.correction.qt import compute_qt
from geoview_cpt.correction.stress import compute_sigma_prime_v0, compute_sigma_v0
from geoview_cpt.correction.u0 import hydrostatic_pressure
from geoview_cpt.derivation.ic import compute_fr_normalized
from geoview_cpt.derivation.qtn import compute_qtn_iterative
from geoview_cpt.derivation.rf import compute_rf
from geoview_cpt.model import CPTChannel, CPTHeader, CPTSounding


# ---------------------------------------------------------------------------
# Group list contract
# ---------------------------------------------------------------------------


class TestCoreGroups:
    def test_has_five_core_groups(self):
        assert set(AGS4_CORE_GROUPS.keys()) == {
            "PROJ", "LOCA", "SCPG", "SCPT", "SCPP"
        }

    def test_scpg_has_cone_area_fields(self):
        assert "SCPG_CARD" in AGS4_CORE_GROUPS["SCPG"]
        assert "SCPG_CAR" in AGS4_CORE_GROUPS["SCPG"]

    def test_scpt_has_raw_qc_fs_u2(self):
        for k in ("SCPT_RES", "SCPT_FRES", "SCPT_PWP2"):
            assert k in AGS4_CORE_GROUPS["SCPT"]


# ---------------------------------------------------------------------------
# Synthetic bare sounding → every core field missing
# ---------------------------------------------------------------------------


class TestBareAudit:
    def test_empty_sounding_report(self):
        s = CPTSounding(handle=0, element_tag="", name="bare")
        report = audit_missing_fields(s)
        assert isinstance(report, AuditReport)
        # No header, no channels → everything missing
        assert report.total_present == 0
        assert "PROJ_NAME" in report.missing_by_group["PROJ"]
        assert "LOCA_ID" in report.missing_by_group["LOCA"]
        assert "SCPT_DPTH" in report.missing_by_group["SCPT"]


# ---------------------------------------------------------------------------
# Fully-populated synthetic sounding (JAKO-shaped)
# ---------------------------------------------------------------------------


def _jako_shaped_sounding() -> CPTSounding:
    s = CPTSounding(handle=0, element_tag="", name="CPT01")
    s.header = CPTHeader(
        sounding_id="CPT01",
        project_name="JAKO",
        partner_name="Geoview",
        equipment_model="WISON-APB",
        cone_base_area_mm2=200.0,
        cone_area_ratio_a=0.7032,
        water_depth_m=88.0,
    )
    depth = np.linspace(0.0, 4.0, 200)
    s.channels = {
        "depth": CPTChannel(name="depth", unit="m",   values=depth),
        "qc":    CPTChannel(name="qc",    unit="MPa", values=np.linspace(0.01, 5.0, 200)),
        "fs":    CPTChannel(name="fs",    unit="kPa", values=np.linspace(1.0, 50.0, 200)),
        "u2":    CPTChannel(name="u2",    unit="kPa", values=np.linspace(10.0, 80.0, 200)),
    }
    qt = compute_qt(s.channels["qc"], s.channels["u2"], a=0.7032)
    u0 = hydrostatic_pressure(s.channels["depth"])
    sv0 = compute_sigma_v0(s.channels["depth"], gamma=18.0)
    spv0 = compute_sigma_prime_v0(sv0, u0)
    fr = compute_fr_normalized(s.channels["fs"], qt, sv0)
    qtn = compute_qtn_iterative(qt, s.channels["fs"], sv0, spv0)
    s.derived = {
        "qt": qt,
        "u0": u0,
        "sigma_v0": sv0,
        "sigma_prime_v0": spv0,
        "Rf": compute_rf(s.channels["fs"], qt),
        "Fr": fr,
        "Bq": CPTChannel(name="Bq", unit="-", values=np.zeros_like(depth)),
        "Qtn": qtn.qtn,
        "Ic": qtn.ic,
    }
    return s


class TestJakoShapedAudit:
    def test_proj_name_present(self):
        report = audit_missing_fields(_jako_shaped_sounding())
        assert "PROJ_NAME" in report.present_by_group["PROJ"]

    def test_proj_id_missing(self):
        """JAKO bundles never carry PROJ_ID — Week 13 writer must inject."""
        report = audit_missing_fields(_jako_shaped_sounding())
        assert "PROJ_ID" in report.missing_by_group["PROJ"]

    def test_loca_id_present(self):
        report = audit_missing_fields(_jako_shaped_sounding())
        assert "LOCA_ID" in report.present_by_group["LOCA"]

    def test_scpg_cone_geometry_present(self):
        report = audit_missing_fields(_jako_shaped_sounding())
        assert "SCPG_CARD" in report.present_by_group["SCPG"]
        assert "SCPG_CAR" in report.present_by_group["SCPG"]
        assert "SCPG_TYPE" in report.present_by_group["SCPG"]

    def test_scpg_crew_missing(self):
        """SCPG_CREW is never recorded in JAKO — flag for override."""
        report = audit_missing_fields(_jako_shaped_sounding())
        assert "SCPG_CREW" in report.missing_by_group["SCPG"]

    def test_scpt_raw_channels_present(self):
        report = audit_missing_fields(_jako_shaped_sounding())
        for k in ("SCPT_DPTH", "SCPT_RES", "SCPT_FRES", "SCPT_PWP2"):
            assert k in report.present_by_group["SCPT"]

    def test_scpt_derived_columns_present_after_derivation(self):
        report = audit_missing_fields(_jako_shaped_sounding())
        assert "SCPT_QT" in report.present_by_group["SCPT"]
        assert "SCPT_FR" in report.present_by_group["SCPT"]

    def test_scpp_ic_present_after_qtn(self):
        report = audit_missing_fields(_jako_shaped_sounding())
        assert "SCPP_IC" in report.present_by_group["SCPP"]


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------


class TestMarkdown:
    def test_markdown_structure(self):
        report = audit_missing_fields(_jako_shaped_sounding())
        md = report.as_markdown()
        assert md.startswith("# A3 JAKO Missing Field Audit")
        # Each of the 5 groups has a level-2 header
        for group in AGS4_CORE_GROUPS:
            assert f"## {group}" in md
        # Notes section present
        assert "## Notes" in md


# ---------------------------------------------------------------------------
# Real JAKO CPT01 bundle — optional H: drive
# ---------------------------------------------------------------------------


_REAL_CDF = Path(
    r"H:/자코/JAKO_Korea_area/Raw_data/Jako_Korea_area_CPT_raw_data/CPT01/CPT010001.cdf"
)
_REAL_CLOG = Path(
    r"H:/자코/JAKO_Korea_area/Raw_data/Jako_Korea_area_CPT_raw_data/CPT01/CPT010001.CLog"
)

jako_required = pytest.mark.skipif(
    not (_REAL_CDF.exists() and _REAL_CLOG.exists()),
    reason="JAKO CPT01 vendor bundle not mounted",
)


@jako_required
class TestRealJakoAudit:
    def _real_sounding(self):
        from geoview_cpt.parsers.cpt_text_bundle import parse_cdf_bundle

        s = parse_cdf_bundle(_REAL_CDF)
        qt = compute_qt(s.channels["qc"], s.channels["u2"], a=s.header.cone_area_ratio_a or 0.7032)
        u0 = hydrostatic_pressure(s.channels["depth"])
        sv0 = compute_sigma_v0(s.channels["depth"], gamma=18.0)
        spv0 = compute_sigma_prime_v0(sv0, u0)
        fr = compute_fr_normalized(s.channels["fs"], qt, sv0)
        qtn = compute_qtn_iterative(qt, s.channels["fs"], sv0, spv0)
        s.derived = {
            "qt": qt,
            "u0": u0,
            "sigma_v0": sv0,
            "sigma_prime_v0": spv0,
            "Fr": fr,
            "Rf": compute_rf(s.channels["fs"], qt),
            "Bq": CPTChannel(name="Bq", unit="-", values=np.zeros_like(s.channels["depth"].values)),
            "Qtn": qtn.qtn,
            "Ic": qtn.ic,
        }
        return s

    def test_report_runs(self):
        report = audit_missing_fields(self._real_sounding())
        assert isinstance(report, AuditReport)

    def test_real_jako_missing_headings(self):
        report = audit_missing_fields(self._real_sounding())
        # R-new closure: confirm the specific missing fields Week 13
        # writer needs to either prompt or synthesize
        assert "PROJ_ID" in report.missing_by_group["PROJ"]
        assert "SCPG_CREW" in report.missing_by_group["SCPG"]
        assert "LOCA_NATE" in report.missing_by_group["LOCA"]
