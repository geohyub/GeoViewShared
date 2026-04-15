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

Week 14 scope: Week 13 core + GEOL (from sounding.strata) and a new
``build_gi_bundle`` / ``write_gi_ags`` pair that emits LOCA / GEOL /
SAMP / ISPT from a :class:`geoview_gi.minimal_model.Borehole`.

``on_missing`` policy:

    "omit"            — default. Missing fields emit empty strings.
    "inject_default"  — Week 14 B. Read defaults from a YAML config
                        file via :mod:`ags_convert.defaults_config`
                        and substitute blank fields before emission.
    "prompt"          — Phase B CPTPrep UI consumer. Out of scope for
                        the backend writer (raises NotImplementedError).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pandas as pd

from geoview_cpt.ags_convert.groups import (
    build_geol,
    build_ispt,
    build_loca,
    build_loca_from_borehole,
    build_proj,
    build_samp,
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
    from geoview_gi.minimal_model import Borehole

__all__ = [
    "ProjectMeta",
    "OnMissingPolicy",
    "write_ags",
    "write_gi_ags",
    "build_core_bundle",
    "build_gi_bundle",
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
    meta = _resolve_meta(project_meta, on_missing)

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

    # GEOL — only included when stratigraphy is attached to the sounding
    geol_df = None
    if getattr(sounding, "strata", None):
        geol_df = build_geol(sounding.name, sounding.strata)

    # Global UNIT / TYPE dictionaries — scan every populated group
    tables_for_dict: dict[str, pd.DataFrame] = {
        "PROJ": proj_df,
        "TRAN": tran_df,
        "LOCA": loca_df,
        "SCPG": scpg_df,
        "SCPT": scpt_df,
        "SCPP": scpp_df,
    }
    if geol_df is not None:
        tables_for_dict["GEOL"] = geol_df
    used_units = _collect_units(tables_for_dict)
    used_types = _collect_types(tables_for_dict)
    unit_df = build_unit_dictionary(used_units)
    type_df = build_type_dictionary(used_types)

    tables: dict[str, pd.DataFrame] = {
        "PROJ": proj_df,
        "TRAN": tran_df,
        "UNIT": unit_df,
        "TYPE": type_df,
        "LOCA": loca_df,
        "SCPG": scpg_df,
        "SCPT": scpt_df,
        "SCPP": scpp_df,
    }
    if geol_df is not None:
        tables["GEOL"] = geol_df
    headings = {g: list(df.columns) for g, df in tables.items()}
    bundle = AGSBundle(tables=tables, headings=headings)
    bundle.build_unit_map()
    return bundle


def build_gi_bundle(
    borehole: "Borehole",
    *,
    project_meta: ProjectMeta | dict | None = None,
    on_missing: OnMissingPolicy = "omit",
) -> AGSBundle:
    """
    Build an :class:`AGSBundle` for a ground-investigation borehole.

    Emits PROJ / TRAN / UNIT / TYPE / LOCA / GEOL / SAMP / ISPT from a
    :class:`geoview_gi.minimal_model.Borehole`. When ``borehole.strata``
    / ``borehole.samples`` / ``borehole.spt_tests`` are empty, the
    corresponding GROUP is omitted from the bundle entirely (AGS4 does
    not require every GROUP, only that populated rows are valid).
    """
    meta = _resolve_meta(project_meta, on_missing)

    tran_df = build_tran(
        issue_no=(meta.tran_issue_no if meta else "1"),
        status=(meta.tran_status if meta else "DRAFT"),
        description=(meta.tran_description if meta else ""),
        recipient=(meta.tran_recipient if meta else ""),
    )
    proj_df = build_proj(meta)
    loca_df = build_loca_from_borehole(borehole, meta)

    tables: dict[str, pd.DataFrame] = {
        "PROJ": proj_df,
        "TRAN": tran_df,
        "LOCA": loca_df,
    }
    if borehole.strata:
        tables["GEOL"] = build_geol(borehole.loca_id, borehole.strata)
    if borehole.samples:
        tables["SAMP"] = build_samp(borehole.samples)
    if borehole.spt_tests:
        tables["ISPT"] = build_ispt(borehole.loca_id, borehole.spt_tests)

    used_units = _collect_units(tables)
    used_types = _collect_types(tables)
    unit_df = build_unit_dictionary(used_units)
    type_df = build_type_dictionary(used_types)

    ordered: dict[str, pd.DataFrame] = {
        "PROJ": proj_df,
        "TRAN": tran_df,
        "UNIT": unit_df,
        "TYPE": type_df,
        "LOCA": loca_df,
    }
    for g in ("GEOL", "SAMP", "ISPT"):
        if g in tables:
            ordered[g] = tables[g]
    headings = {g: list(df.columns) for g, df in ordered.items()}
    bundle = AGSBundle(tables=ordered, headings=headings)
    bundle.build_unit_map()
    return bundle


def _resolve_meta(
    project_meta: ProjectMeta | dict | None,
    on_missing: OnMissingPolicy,
) -> ProjectMeta | None:
    if on_missing == "prompt":
        raise NotImplementedError(
            "on_missing='prompt' is reserved for Phase B CPTPrep UI"
        )
    if on_missing not in ("omit", "inject_default"):
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

    if on_missing == "inject_default":
        # Defer to the Week 14B defaults config. Imported lazily so tests
        # that do not touch the feature don't pay the import cost.
        from geoview_cpt.ags_convert.defaults_config import apply_defaults

        meta = apply_defaults(meta)
    return meta


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
    except (NotImplementedError, AgsConvertError):
        raise
    except Exception as exc:
        raise AgsConvertError(
            f"core bundle build failed for sounding {sounding.name!r}: {exc}"
        ) from exc
    return dump_ags(bundle, path)


def write_gi_ags(
    borehole: "Borehole",
    path: Path | str,
    *,
    project_meta: ProjectMeta | dict | None = None,
    on_missing: OnMissingPolicy = "omit",
) -> Path:
    """
    Write a :class:`Borehole` to an ``.ags`` file (GI pipeline).

    Emits LOCA + GEOL / SAMP / ISPT (only the GROUPs with data), plus
    the mandatory PROJ / TRAN / UNIT / TYPE header block. The GI path
    does not emit SCPG / SCPT / SCPP — use :func:`write_ags` with a
    :class:`CPTSounding` for the CPT pipeline.
    """
    try:
        bundle = build_gi_bundle(
            borehole, project_meta=project_meta, on_missing=on_missing
        )
    except (NotImplementedError, AgsConvertError):
        raise
    except Exception as exc:
        raise AgsConvertError(
            f"gi bundle build failed for borehole {borehole.loca_id!r}: {exc}"
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
