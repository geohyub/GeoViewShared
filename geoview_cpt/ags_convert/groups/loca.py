"""
geoview_cpt.ags_convert.groups.loca
=======================================
LOCA GROUP writer — one row per sounding.

Pulls what the A-2 ``CPTHeader`` can supply (sounding_id, coordinates,
final depth, start/end dates) and fills the rest from
:class:`ProjectMeta`. Values the parser leaves blank are emitted as
empty strings under the Week 13 ``on_missing="omit"`` policy.

JAKO CPT01 observation: ``LOCA_NATE`` / ``LOCA_NATN`` ship as zero
from the vendor text bundle (operator left them blank). The writer
does not transform zeros into blanks — Week 14 writer refinement can
add a ``coordinates_required=True`` flag if the Kingdom workflow
demands it.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from geoview_cpt.ags_convert.groups._helpers import (
    build_table,
    format_date_iso,
    format_decimal,
    safe_text,
)
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.writer import ProjectMeta

__all__ = ["LOCA_COLUMNS", "LOCA_UNITS", "LOCA_TYPES", "build_loca"]


LOCA_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "LOCA_TYPE",
    "LOCA_STAT",
    "LOCA_NATE",
    "LOCA_NATN",
    "LOCA_GREF",
    "LOCA_GL",
    "LOCA_FDEP",
    "LOCA_STAR",
    "LOCA_ENDD",
    "LOCA_CLNT",
    "LOCA_PURP",
)

LOCA_UNITS: tuple[str, ...] = (
    "",           # HEADING
    "",           # LOCA_ID
    "",           # LOCA_TYPE
    "",           # LOCA_STAT
    "m",          # LOCA_NATE
    "m",          # LOCA_NATN
    "",           # LOCA_GREF
    "m",          # LOCA_GL
    "m",          # LOCA_FDEP
    "yyyy-mm-dd", # LOCA_STAR
    "yyyy-mm-dd", # LOCA_ENDD
    "",           # LOCA_CLNT
    "",           # LOCA_PURP
)

LOCA_TYPES: tuple[str, ...] = (
    "",     # HEADING
    "ID",
    "PA",
    "PA",
    "2DP",
    "2DP",
    "PA",
    "2DP",
    "2DP",
    "DT",
    "DT",
    "X",
    "X",
)


def build_loca(
    sounding: CPTSounding,
    project_meta: "ProjectMeta | None",
) -> pd.DataFrame:
    """
    Build the LOCA GROUP DataFrame (single row per sounding).

    Args:
        sounding:     :class:`CPTSounding` with header populated.
        project_meta: optional :class:`ProjectMeta` supplying LOCA_CLNT
                      / LOCA_PURP / LOCA_GREF / LOCA_TYPE / LOCA_STAT.
    """
    header = sounding.header

    loca_id = sounding.name
    loca_type = ""
    loca_stat = ""
    loca_gref = ""
    loca_clnt = ""
    loca_purp = ""
    if project_meta is not None:
        loca_type = safe_text(project_meta.loca_type)
        loca_stat = safe_text(project_meta.loca_status)
        loca_gref = safe_text(project_meta.crs)
        loca_clnt = safe_text(project_meta.client)
        loca_purp = safe_text(project_meta.loca_purpose)

    nate = ""
    natn = ""
    gl = ""
    fdep = format_decimal(sounding.max_depth_m, decimals=2)
    star = ""
    endd = ""

    if header is not None:
        if header.loca_x is not None:
            nate = format_decimal(header.loca_x, decimals=2)
        if header.loca_y is not None:
            natn = format_decimal(header.loca_y, decimals=2)
        if header.water_depth_m is not None:
            gl = format_decimal(header.water_depth_m, decimals=2)
        if header.max_push_depth_m is not None:
            fdep = format_decimal(header.max_push_depth_m, decimals=2)
        if header.started_at is not None:
            star = format_date_iso(header.started_at)
        if header.completed_at is not None:
            endd = format_date_iso(header.completed_at)

    row = {
        "LOCA_ID":   safe_text(loca_id),
        "LOCA_TYPE": loca_type,
        "LOCA_STAT": loca_stat,
        "LOCA_NATE": nate,
        "LOCA_NATN": natn,
        "LOCA_GREF": loca_gref,
        "LOCA_GL":   gl,
        "LOCA_FDEP": fdep,
        "LOCA_STAR": star,
        "LOCA_ENDD": endd,
        "LOCA_CLNT": loca_clnt,
        "LOCA_PURP": loca_purp,
    }
    return build_table(LOCA_COLUMNS, LOCA_UNITS, LOCA_TYPES, [row])
