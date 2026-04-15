"""
geoview_cpt.ags_convert.groups.proj
=======================================
PROJ GROUP writer — project-level metadata.

The PROJ group has a single DATA row per AGS4 file. Content comes
from :class:`ProjectMeta` because the A-2 parsers do not carry
project-level identifiers (JAKO CPT01 leaves ``PROJ_ID`` /
``PROJ_LOC`` / ``PROJ_ENG`` blank — see
``docs/a3_jako_missing_fields.md``).

Week 13 ``on_missing="omit"`` policy: any field not supplied by the
caller is emitted as an empty string. Week 14 will add
``inject_default`` to fill from a per-project YAML.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from geoview_cpt.ags_convert.groups._helpers import build_table, safe_text

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.writer import ProjectMeta

__all__ = ["PROJ_COLUMNS", "PROJ_UNITS", "PROJ_TYPES", "build_proj"]


PROJ_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "PROJ_ID",
    "PROJ_NAME",
    "PROJ_LOC",
    "PROJ_CLNT",
    "PROJ_CONT",
    "PROJ_ENG",
    "PROJ_MEMO",
)

PROJ_UNITS: tuple[str, ...] = ("",) * len(PROJ_COLUMNS)

PROJ_TYPES: tuple[str, ...] = (
    "",      # HEADING
    "ID",
    "X",
    "X",
    "X",
    "X",
    "X",
    "X",
)


def build_proj(project_meta: "ProjectMeta | None") -> pd.DataFrame:
    """
    Build the PROJ GROUP DataFrame.

    Args:
        project_meta: source of PROJ_* values. When ``None`` every
                      field comes out blank — the AGS4 writer still
                      emits a valid group, just with empty cells.

    Returns:
        DataFrame in UNIT/TYPE/DATA layout.
    """
    row: dict[str, str] = {
        "PROJ_ID":   "",
        "PROJ_NAME": "",
        "PROJ_LOC":  "",
        "PROJ_CLNT": "",
        "PROJ_CONT": "",
        "PROJ_ENG":  "",
        "PROJ_MEMO": "",
    }
    if project_meta is not None:
        row["PROJ_ID"] = safe_text(project_meta.project_id)
        row["PROJ_NAME"] = safe_text(project_meta.project_name)
        row["PROJ_LOC"] = safe_text(project_meta.project_location)
        row["PROJ_CLNT"] = safe_text(project_meta.client)
        row["PROJ_CONT"] = safe_text(project_meta.contractor)
        row["PROJ_ENG"] = safe_text(project_meta.engineer)
        row["PROJ_MEMO"] = safe_text(project_meta.memo)
    return build_table(PROJ_COLUMNS, PROJ_UNITS, PROJ_TYPES, [row])
