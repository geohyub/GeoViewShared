"""
geoview_cpt.ags_convert.jako_audit
======================================
Smoke audit of the JAKO CPT01 vendor bundle against the AGS4 v4.1.1
standard dictionary (Phase A-3 Week 12, R-new closure).

Purpose:

    Produce ``audit_missing_fields(sounding)`` → a structured list of
    AGS4 HEADINGs that the A2.0/A2.2d parsers leave empty. The Week 13
    writer (A3.2) uses this list to decide which columns need synthetic
    defaults, which need user-supplied overrides, and which can be
    silently omitted.

This is **not** a full AGS4 writer — it only introspects the canonical
:class:`CPTSounding` shape and compares it against the AGS4 HEADINGs
for the core marine-CPT GROUPs (PROJ / LOCA / SCPG / SCPT / SCPP). No
DataFrame is written; the output is a plain :class:`AuditReport`
dataclass that tests and the Week 13 writer can consume directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geoview_cpt.model import CPTSounding

__all__ = [
    "AuditReport",
    "AGS4_CORE_GROUPS",
    "audit_missing_fields",
]


# ---------------------------------------------------------------------------
# Expected headings — core marine CPT subset (Wave 0 plan §5.3)
# ---------------------------------------------------------------------------


AGS4_CORE_GROUPS: dict[str, list[str]] = {
    # Project metadata
    "PROJ": [
        "PROJ_ID", "PROJ_NAME", "PROJ_LOC", "PROJ_CLNT",
        "PROJ_CONT", "PROJ_ENG", "PROJ_MEMO",
    ],
    # Location (one row per borehole / sounding)
    "LOCA": [
        "LOCA_ID", "LOCA_TYPE", "LOCA_STAT",
        "LOCA_NATE", "LOCA_NATN", "LOCA_GREF",
        "LOCA_GL", "LOCA_FDEP", "LOCA_STAR", "LOCA_ENDD",
        "LOCA_CLNT", "LOCA_PURP",
    ],
    # SCPG — static cone penetration test, general
    "SCPG": [
        "LOCA_ID", "SCPG_TESN", "SCPG_TYPE", "SCPG_CREW",
        "SCPG_TESD", "SCPG_TESM", "SCPG_DTIM",
        "SCPG_CARD", "SCPG_FARD", "SCPG_CAR",
    ],
    # SCPT — static cone penetration test, depth data (raw qc/fs/u2)
    "SCPT": [
        "LOCA_ID", "SCPT_TESN", "SCPT_DPTH",
        "SCPT_RES", "SCPT_FRES", "SCPT_PWP2",
        "SCPT_QT", "SCPT_FR", "SCPT_BQ",
    ],
    # SCPP — static cone penetration test, pore dissipation / profile
    "SCPP": [
        "LOCA_ID", "SCPP_TESN", "SCPP_DPTH",
        "SCPP_COH", "SCPP_PHI", "SCPP_DEN",
        "SCPP_IC", "SCPP_NKT", "SCPP_REM",
    ],
}


@dataclass
class AuditReport:
    """One row per GROUP describing missing HEADINGs."""

    missing_by_group: dict[str, list[str]] = field(default_factory=dict)
    present_by_group: dict[str, list[str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def total_missing(self) -> int:
        return sum(len(v) for v in self.missing_by_group.values())

    @property
    def total_present(self) -> int:
        return sum(len(v) for v in self.present_by_group.values())

    def as_markdown(self) -> str:
        lines = ["# A3 JAKO Missing Field Audit", ""]
        lines.append(
            f"Total missing HEADINGs: **{self.total_missing}**   ·   "
            f"Total populated: **{self.total_present}**"
        )
        lines.append("")
        for group in AGS4_CORE_GROUPS:
            missing = self.missing_by_group.get(group, [])
            present = self.present_by_group.get(group, [])
            lines.append(f"## {group}")
            lines.append("")
            if present:
                lines.append(f"- Populated ({len(present)}): {', '.join(present)}")
            if missing:
                lines.append(f"- **Missing ({len(missing)})**: {', '.join(missing)}")
            lines.append("")
        if self.notes:
            lines.append("## Notes")
            for n in self.notes:
                lines.append(f"- {n}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def audit_missing_fields(sounding: "CPTSounding") -> AuditReport:
    """
    Compare ``sounding`` against the AGS4 core group HEADINGs and
    return an :class:`AuditReport`.

    The check is deliberately coarse — it looks at ``CPTHeader`` plus
    the well-known channel names (``depth``, ``qc``, ``fs``, ``u2``,
    ``Ic`` …) and decides "present" when the underlying value is
    non-empty / non-default. Sub-typed missing details (e.g. SCPG_CREW
    as a crew name string) are flagged so the writer can surface them
    as user-override prompts.
    """
    header = sounding.header

    report = AuditReport()

    # PROJ -------------------------------------------------------------------
    proj_missing: list[str] = []
    proj_present: list[str] = []
    if header is None:
        proj_missing = list(AGS4_CORE_GROUPS["PROJ"])
    else:
        if _has_text(header.project_name):
            proj_present.append("PROJ_NAME")
        else:
            proj_missing.append("PROJ_NAME")
        if _has_text(header.client):
            proj_present.append("PROJ_CLNT")
        else:
            proj_missing.append("PROJ_CLNT")
        if _has_text(header.partner_name):
            proj_present.append("PROJ_CONT")
        else:
            proj_missing.append("PROJ_CONT")
        # IDs and memos typically absent in JAKO
        for key in ("PROJ_ID", "PROJ_LOC", "PROJ_ENG", "PROJ_MEMO"):
            proj_missing.append(key)
    report.missing_by_group["PROJ"] = proj_missing
    report.present_by_group["PROJ"] = proj_present

    # LOCA -------------------------------------------------------------------
    loca_missing: list[str] = []
    loca_present: list[str] = []
    if header is None:
        loca_missing = list(AGS4_CORE_GROUPS["LOCA"])
    else:
        if _has_text(header.sounding_id):
            loca_present.append("LOCA_ID")
        else:
            loca_missing.append("LOCA_ID")
        if header.water_depth_m is not None and header.water_depth_m > 0:
            loca_present.append("LOCA_GL")
        else:
            loca_missing.append("LOCA_GL")
        if header.loca_x is not None:
            loca_present.append("LOCA_NATE")
        else:
            loca_missing.append("LOCA_NATE")
        if header.loca_y is not None:
            loca_present.append("LOCA_NATN")
        else:
            loca_missing.append("LOCA_NATN")
        if header.completed_at is not None or header.started_at is not None:
            loca_present.append("LOCA_STAR")
        else:
            loca_missing.append("LOCA_STAR")
        for key in ("LOCA_TYPE", "LOCA_STAT", "LOCA_GREF",
                    "LOCA_FDEP", "LOCA_ENDD", "LOCA_CLNT", "LOCA_PURP"):
            if key not in loca_present:
                loca_missing.append(key)
    report.missing_by_group["LOCA"] = loca_missing
    report.present_by_group["LOCA"] = loca_present

    # SCPG -------------------------------------------------------------------
    scpg_missing: list[str] = []
    scpg_present: list[str] = []
    if header is None:
        scpg_missing = list(AGS4_CORE_GROUPS["SCPG"])
    else:
        scpg_present.append("LOCA_ID")
        if header.cone_base_area_mm2 and header.cone_base_area_mm2 > 0:
            scpg_present.append("SCPG_CARD")   # cone area
        else:
            scpg_missing.append("SCPG_CARD")
        if header.cone_area_ratio_a and header.cone_area_ratio_a > 0:
            scpg_present.append("SCPG_CAR")    # area ratio
        else:
            scpg_missing.append("SCPG_CAR")
        if _has_text(header.equipment_model):
            scpg_present.append("SCPG_TYPE")
        else:
            scpg_missing.append("SCPG_TYPE")
        for key in ("SCPG_TESN", "SCPG_CREW", "SCPG_TESD",
                    "SCPG_TESM", "SCPG_DTIM", "SCPG_FARD"):
            scpg_missing.append(key)
    report.missing_by_group["SCPG"] = scpg_missing
    report.present_by_group["SCPG"] = scpg_present

    # SCPT (raw profile) -----------------------------------------------------
    scpt_missing: list[str] = []
    scpt_present: list[str] = []
    if "depth" in sounding.channels:
        scpt_present.extend(["LOCA_ID", "SCPT_DPTH"])
    else:
        scpt_missing.extend(["LOCA_ID", "SCPT_DPTH"])
    if "qc" in sounding.channels:
        scpt_present.append("SCPT_RES")
    else:
        scpt_missing.append("SCPT_RES")
    if "fs" in sounding.channels:
        scpt_present.append("SCPT_FRES")
    else:
        scpt_missing.append("SCPT_FRES")
    if "u2" in sounding.channels:
        scpt_present.append("SCPT_PWP2")
    else:
        scpt_missing.append("SCPT_PWP2")
    if "qt" in sounding.derived:
        scpt_present.append("SCPT_QT")
    else:
        scpt_missing.append("SCPT_QT")
    if "Fr" in sounding.derived or "Rf" in sounding.derived:
        scpt_present.append("SCPT_FR")
    else:
        scpt_missing.append("SCPT_FR")
    if "Bq" in sounding.derived:
        scpt_present.append("SCPT_BQ")
    else:
        scpt_missing.append("SCPT_BQ")
    scpt_missing.append("SCPT_TESN")    # test number — not recorded in JAKO
    report.missing_by_group["SCPT"] = scpt_missing
    report.present_by_group["SCPT"] = scpt_present

    # SCPP (derived parameters) ---------------------------------------------
    scpp_missing: list[str] = []
    scpp_present: list[str] = []
    if "depth" in sounding.channels:
        scpp_present.extend(["LOCA_ID", "SCPP_DPTH"])
    else:
        scpp_missing.extend(["LOCA_ID", "SCPP_DPTH"])
    if "Ic" in sounding.derived:
        scpp_present.append("SCPP_IC")
    else:
        scpp_missing.append("SCPP_IC")
    # SCPP_NKT default (15/30) comes from CPeT-IT Various — only count
    # it "present" when the sounding carries a derivation chain (a
    # reasonable proxy for "CPeT-IT default has been consulted").
    if header is not None and "qt" in sounding.derived:
        scpp_present.append("SCPP_NKT")
    else:
        scpp_missing.append("SCPP_NKT")
    for key in ("SCPP_TESN", "SCPP_COH", "SCPP_PHI", "SCPP_DEN", "SCPP_REM"):
        scpp_missing.append(key)
    report.missing_by_group["SCPP"] = scpp_missing
    report.present_by_group["SCPP"] = scpp_present

    report.notes.append(
        "JAKO bundle lacks PROJ_ID / LOCA_GREF / SCPG_CREW — Week 13 "
        "writer must prompt user for overrides or inject sentinel values."
    )
    report.notes.append(
        "SCPT derived columns (QT/FR/BQ) populate only after the "
        "derivation chain (geoview_cpt.correction + .derivation) runs."
    )

    return report


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _has_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())
