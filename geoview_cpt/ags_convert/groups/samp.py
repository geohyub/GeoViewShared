"""
geoview_cpt.ags_convert.groups.samp
=======================================
SAMP GROUP writer — lab samples, one row per :class:`LabSample`.

Source: ``borehole.samples``. The 17-field ``LabSample`` contract
(see :class:`geoview_gi.minimal_model.LabSample`) maps onto the AGS4
SAMP KEY columns plus a handful of OTHER columns the A-2 parser
carries.

Column mapping (AGS4 v4.1.1 DICT, KEY columns first):

    LOCA_ID   ← LabSample.loca_id               (ID / KEY)
    SAMP_TOP  ← LabSample.top_m         (m, 2DP / KEY)
    SAMP_REF  ← LabSample.sample_ref            (X  / KEY)
    SAMP_TYPE ← LabSample.sample_type           (PA / KEY)
    SAMP_ID   ← LabSample.sample_id             (ID / KEY)
    SAMP_BASE ← LabSample.base_m        (m, 2DP)
    SAMP_RECV ← LabSample.recovery_pct  (%,  0DP)

The lab-result slots (moisture content, Atterberg, Su, phi') live in
the downstream test-result groups (SAMP is identity only in AGS4).
They are therefore **not** written here; Week 15 A3.4 GEOLAB exporter
picks them up.

``SAMP_TYPE`` comes through as a literal ``LabSample.sample_type``
string — the SampleType Literal is the vendor-neutral alphabet the
PL / lab parsers emit, so the value is already AGS4-compatible.
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
    from geoview_gi.minimal_model import LabSample

__all__ = ["SAMP_COLUMNS", "SAMP_UNITS", "SAMP_TYPES", "build_samp"]


SAMP_COLUMNS: tuple[str, ...] = (
    "HEADING",
    "LOCA_ID",
    "SAMP_TOP",
    "SAMP_REF",
    "SAMP_TYPE",
    "SAMP_ID",
    "SAMP_BASE",
    "SAMP_RECV",
)

SAMP_UNITS: tuple[str, ...] = (
    "",
    "",
    "m",
    "",
    "",
    "",
    "m",
    "%",
)

SAMP_TYPES: tuple[str, ...] = (
    "",
    "ID",
    "2DP",
    "X",
    "PA",
    "ID",
    "2DP",
    "0DP",
)


def build_samp(samples: "Iterable[LabSample]") -> pd.DataFrame:
    """
    Build the SAMP GROUP DataFrame.

    Args:
        samples: iterable of :class:`LabSample` — usually
                 ``borehole.samples``. ``sample.loca_id`` must already
                 be populated by the parser (the SAMP KEY is
                 (LOCA_ID, SAMP_TOP, SAMP_REF, SAMP_TYPE, SAMP_ID)).
    """
    rows: list[dict[str, str]] = []
    for samp in samples:
        row = {
            "LOCA_ID":   safe_text(samp.loca_id),
            "SAMP_TOP":  format_decimal(samp.top_m, decimals=2),
            "SAMP_REF":  safe_text(samp.sample_ref),
            "SAMP_TYPE": safe_text(samp.sample_type),
            "SAMP_ID":   safe_text(samp.sample_id),
            "SAMP_BASE": format_decimal(samp.base_m, decimals=2),
            "SAMP_RECV": format_decimal(samp.recovery_pct, decimals=0),
        }
        rows.append(row)
    return build_table(SAMP_COLUMNS, SAMP_UNITS, SAMP_TYPES, rows)
