"""
geoview_cpt.ags_convert.writer
================================
AGS4 writer — orchestrator for the per-GROUP builders (Phase A-3
Week 13 A3.2).

Public API:

    ProjectMeta     dataclass — project-level fields the A-2 parsers
                    don't carry (PROJ_ID / PROJ_LOC / LOCA_GREF etc.)
    write_ags       CPTSounding → .ags file
    build_core_bundle
                    CPTSounding → AGSBundle without writing (handy for
                    tests and the Week 14 validator)

Week 13 scope: 8 core GROUPs (PROJ/TRAN/UNIT/TYPE/LOCA/SCPG/SCPT/SCPP).
GEOL / HOLE / SAMP / ISPT arrive in Week 14 A3.2 Part 2.

``on_missing`` policy:

    "omit"            — default. Missing fields emit empty strings.
                        Week 13 uses this for every caller.
    "inject_default"  — Week 14. Read defaults from a config file.
    "prompt"          — Phase B CPTPrep UI consumer. Out of scope for
                        the backend writer (raises NotImplementedError).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pandas as pd

from geoview_cpt.ags_convert.groups import (
    build_loca,
    build_proj,
    build_scpg,
    build_scpp,
    build_scpt,
    build_tran,
    build_type_dictionary,
    build_unit_dictionary,
)
from geoview_cpt.ags_convert.wrapper import AGSBundle, AgsConvertError, dump_ags

if TYPE_CHECKING:
    from geoview_cpt.model import CPTSounding

__all__ = [
    "ProjectMeta",
    "OnMissingPolicy",
    "write_ags",
    "build_core_bundle",
]


OnMissingPolicy = Literal["omit", "inject_default", "prompt"]


@dataclass
class ProjectMeta:
    """
    Project-level metadata the A-2 parsers do not carry.

    JAKO CPT01 leaves every PROJ field blank except the vendor
    ``project_name`` / ``client`` strings — see
    ``docs/a3_jako_missing_fields.md``. The caller supplies the rest
    via this dataclass; the writer maps it onto PROJ + LOCA columns.
    """

    # PROJ_* fields
    project_id: str = ""
    project_name: str = ""
    project_location: str = ""
    client: str = ""
    contractor: str = ""
    engineer: str = ""
    memo: str = ""

    # LOCA_* fields
    crs: str = ""
    loca_type: str = ""
    loca_status: str = ""
    loca_purpose: str = ""

    # TRAN_* fields
    tran_status: str = "DRAFT"
    tran_description: str = ""
    tran_recipient: str = ""
    tran_issue_no: str = "1"

    @classmethod
    def from_dict(cls, raw: dict) -> "ProjectMeta":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in raw.items() if k in known})


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_core_bundle(
    sounding: "CPTSounding",
    *,
    project_meta: ProjectMeta | dict | None = None,
    on_missing: OnMissingPolicy = "omit",
) -> AGSBundle:
    """
    Build an :class:`AGSBundle` containing the 8 core Week 13 GROUPs.

    Does not write to disk — tests and the Week 14 validator call this
    directly. :func:`write_ags` wraps it with a :func:`dump_ags` call.
    """
    if on_missing == "prompt":
        raise NotImplementedError(
            "on_missing='prompt' is reserved for Phase B CPTPrep UI"
        )
    if on_missing == "inject_default":
        raise NotImplementedError(
            "on_missing='inject_default' lands in Week 14 (config lookup)"
        )
    if on_missing != "omit":
        raise ValueError(
            f"on_missing must be 'omit' / 'inject_default' / 'prompt', got {on_missing!r}"
        )

    meta: ProjectMeta | None
    if project_meta is None:
        meta = None
    elif isinstance(project_meta, ProjectMeta):
        meta = project_meta
    elif isinstance(project_meta, dict):
        meta = ProjectMeta.from_dict(project_meta)
    else:
        raise TypeError(
            f"project_meta must be ProjectMeta / dict / None, got "
            f"{type(project_meta).__name__}"
        )

    tran_df = build_tran(
        issue_no=(meta.tran_issue_no if meta else "1"),
        status=(meta.tran_status if meta else "DRAFT"),
        description=(meta.tran_description if meta else ""),
        recipient=(meta.tran_recipient if meta else ""),
    )
    proj_df = build_proj(meta)
    loca_df = build_loca(sounding, meta)
    scpg_df = build_scpg(sounding)
    scpt_df = build_scpt(sounding)
    scpp_df = build_scpp(sounding)

    # Global UNIT / TYPE dictionaries — scan every populated group
    tables_for_dict = {
        "PROJ": proj_df,
        "TRAN": tran_df,
        "LOCA": loca_df,
        "SCPG": scpg_df,
        "SCPT": scpt_df,
        "SCPP": scpp_df,
    }
    used_units = _collect_units(tables_for_dict)
    used_types = _collect_types(tables_for_dict)
    unit_df = build_unit_dictionary(used_units)
    type_df = build_type_dictionary(used_types)

    tables = {
        "PROJ": proj_df,
        "TRAN": tran_df,
        "UNIT": unit_df,
        "TYPE": type_df,
        "LOCA": loca_df,
        "SCPG": scpg_df,
        "SCPT": scpt_df,
        "SCPP": scpp_df,
    }
    headings = {g: list(df.columns) for g, df in tables.items()}
    bundle = AGSBundle(tables=tables, headings=headings)
    bundle.build_unit_map()
    return bundle


def write_ags(
    sounding: "CPTSounding",
    path: Path | str,
    *,
    project_meta: ProjectMeta | dict | None = None,
    on_missing: OnMissingPolicy = "omit",
) -> Path:
    """
    Write a :class:`CPTSounding` to an ``.ags`` file.

    Args:
        sounding:      A-2 CPTSounding (must have depth/qc/fs/u2
                       channels; derived qt/Fr/Bq/Ic are optional but
                       recommended).
        path:          output ``.ags`` path (parent directories auto-
                       created).
        project_meta:  :class:`ProjectMeta` or dict supplying the
                       PROJ / LOCA / TRAN fields the A-2 parser can
                       not recover.
        on_missing:    see :data:`OnMissingPolicy`.

    Returns:
        Resolved output path.

    Raises:
        AgsConvertError:      when the writer cannot build or dump
                              the bundle.
        NotImplementedError:  on ``on_missing='prompt'`` or
                              ``'inject_default'`` (Week 13 ships
                              only the ``'omit'`` path).
    """
    try:
        bundle = build_core_bundle(
            sounding, project_meta=project_meta, on_missing=on_missing
        )
    except Exception as exc:
        raise AgsConvertError(
            f"core bundle build failed for sounding {sounding.name!r}: {exc}"
        ) from exc
    return dump_ags(bundle, path)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _collect_units(tables: dict[str, pd.DataFrame]) -> set[str]:
    out: set[str] = set()
    for df in tables.values():
        unit_rows = df[df["HEADING"] == "UNIT"]
        if unit_rows.empty:
            continue
        for col, value in unit_rows.iloc[0].items():
            if col == "HEADING":
                continue
            text = str(value).strip()
            if text:
                out.add(text)
    return out


def _collect_types(tables: dict[str, pd.DataFrame]) -> set[str]:
    out: set[str] = set()
    for df in tables.values():
        type_rows = df[df["HEADING"] == "TYPE"]
        if type_rows.empty:
            continue
        for col, value in type_rows.iloc[0].items():
            if col == "HEADING":
                continue
            text = str(value).strip()
            if text:
                out.add(text)
    return out
