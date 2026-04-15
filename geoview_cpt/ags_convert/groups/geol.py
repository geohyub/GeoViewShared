"""
geoview_cpt.ags_convert.groups.geol
=======================================
GEOL GROUP writer — stratigraphic layers, one row per :class:`StratumLayer`.

Source: ``sounding.strata`` (populated by
``geoview_cpt.stratigraphy.auto_split_by_ic``) or ``borehole.strata``
(populated directly by the GI parser). Both use the same
:class:`geoview_gi.minimal_model.StratumLayer` class, so one builder
serves both code paths.

Column mapping (AGS4 v4.1.1 DICT, Week 14 A3.2 Part 2):

    LOCA_ID   ← loca_id argument
    GEOL_TOP  ← StratumLayer.top_m           (m, 2DP)
    GEOL_BASE ← StratumLayer.base_m          (m, 2DP)
    GEOL_DESC ← StratumLayer.description     (X)
    GEOL_LEG  ← StratumLayer.legend_code     (PA)
    GEOL_GEOL ← StratumLayer.geology_code    (PA)
    GEOL_GEO2 ← StratumLayer.age             (PA)
    GEOL_STAT ← weathering_grade, stringified (X)

``GEOL_BGS`` / ``GEOL_FORM`` / ``GEOL_REM`` are left blank under the
Week 14 ``on_missing='omit'`` policy — the A-2 stratigraphy model does
not carry these fields. The Week 15 config loader will inject defaults
from the per-project YAML when ``on_missing='inject_default'`` ships.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import pandas as pd

from geoview_cpt.ags_convert.groups._helpers import (
    build_table,
    format_decimal,
    safe_text,
)

if TYPE_CHECKING:
    from geoview_gi.minimal_model import StratumLayer

__all__ = ["GEOL_COLUMNS", "GEOL_UNITS", "GEOL_TYPES", "build_geol"]


GEOL_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "GEOL_TOP",
    "GEOL_BASE",
    "GEOL_DESC",
    "GEOL_LEG",
    "GEOL_GEOL",
    "GEOL_GEO2",
    "GEOL_STAT",
    "GEOL_BGS",
    "GEOL_FORM",
    "GEOL_REM",
)

GEOL_UNITS: tuple[str, ...] = (
    "",
    "",
    "m",
    "m",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
)

GEOL_TYPES: tuple[str, ...] = (
    "",
    "ID",
    "2DP",
    "2DP",
    "X",
    "PA",
    "PA",
    "PA",
    "X",
    "PA",
    "X",
    "X",
)


def build_geol(
    loca_id: str,
    strata: "Iterable[StratumLayer]",
) -> pd.DataFrame:
    """
    Build the GEOL GROUP DataFrame.

    Args:
        loca_id: LOCA_ID value for every row (one sounding/borehole).
        strata:  iterable of :class:`StratumLayer` instances — usually
                 ``sounding.strata`` or ``borehole.strata``.

    Returns:
        DataFrame in UNIT/TYPE/DATA layout. An empty ``strata``
        iterable produces a valid GROUP with no DATA rows.
    """
    loca_id_text = safe_text(loca_id)
    rows: list[dict[str, str]] = []
    for layer in strata:
        weath = ""
        if layer.weathering_grade is not None:
            weath = str(int(layer.weathering_grade))
        row = {
            "LOCA_ID":   loca_id_text,
            "GEOL_TOP":  format_decimal(layer.top_m, decimals=2),
            "GEOL_BASE": format_decimal(layer.base_m, decimals=2),
            "GEOL_DESC": safe_text(layer.description),
            "GEOL_LEG":  safe_text(layer.legend_code),
            "GEOL_GEOL": safe_text(layer.geology_code),
            "GEOL_GEO2": safe_text(layer.age),
            "GEOL_STAT": weath,
            "GEOL_BGS":  "",
            "GEOL_FORM": "",
            "GEOL_REM":  "",
        }
        rows.append(row)
    return build_table(GEOL_COLUMNS, GEOL_UNITS, GEOL_TYPES, rows)
