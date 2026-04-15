"""
geoview_cpt.ags_convert.groups
================================
Per-GROUP AGS4 writers (Phase A-3 Week 13 A3.2).

Each module in this package owns the build step for one AGS4 GROUP —
it knows the HEADING list, the UNIT row, the TYPE row, and how to
pull values off a :class:`CPTSounding` or a
:class:`ProjectMeta`. The orchestrator in :mod:`ags_convert.writer`
calls them in sequence and stitches the resulting DataFrames into an
:class:`AGSBundle`.

Public API (re-exported for convenient imports):

    proj.build_proj    PROJ group from ProjectMeta
    tran.build_tran    TRAN group (transmission metadata, auto-filled)
    tran.build_unit_dictionary    UNIT group (global dictionary of units)
    tran.build_type_dictionary    TYPE group (global dictionary of types)
    loca.build_loca    LOCA group from sounding + ProjectMeta
    scpt.build_scpg    SCPG group from sounding.header
    scpt.build_scpt    SCPT per-depth DataFrame (raw + qt/fr/bq)
    scpt.build_scpp    SCPP per-depth DataFrame (Ic, Nkt, ...)

Week 13 scope: 8 GROUPs (PROJ/TRAN/UNIT/TYPE/LOCA/SCPG/SCPT/SCPP).
Week 14 adds GEOL / HOLE / SAMP / ISPT from the stratigraphy + GI
layers.
"""
from __future__ import annotations

from geoview_cpt.ags_convert.groups.geol import build_geol
from geoview_cpt.ags_convert.groups.ispt import build_ispt
from geoview_cpt.ags_convert.groups.loca import build_loca, build_loca_from_borehole
from geoview_cpt.ags_convert.groups.proj import build_proj
from geoview_cpt.ags_convert.groups.samp import build_samp
from geoview_cpt.ags_convert.groups.scpt import build_scpg, build_scpp, build_scpt
from geoview_cpt.ags_convert.groups.tran import (
    build_tran,
    build_type_dictionary,
    build_unit_dictionary,
)

__all__ = [
    "build_proj",
    "build_tran",
    "build_unit_dictionary",
    "build_type_dictionary",
    "build_loca",
    "build_loca_from_borehole",
    "build_scpg",
    "build_scpt",
    "build_scpp",
    "build_geol",
    "build_samp",
    "build_ispt",
]
