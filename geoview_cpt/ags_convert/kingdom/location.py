"""
Kingdom location CSV — Phase A-4 Week 17 A4.3.

A single project-wide CSV listing every CPT/borehole location in the
drop, used by Kingdom to plot the survey grid before the user opens
any of the per-sounding ``.ags`` files. The writer is deliberately
**CRS-agnostic** — coordinates are passed through unchanged from
``LOCA_NATE`` / ``LOCA_NATN`` and the destination CRS responsibility
sits with Kingdom (or the operator's project geodatabase).

Schema::

    LOCA_ID,Easting,Northing,CRS,GL_m,Seabed_m,Water_Depth_m,Type,Date,Remarks

Source: a list of :class:`AGSBundle` (the same per-sounding bundles
the AGS subset writes), or a list of (loca_id, fields_dict) tuples
for callers who want manual control. The convenience overload
:func:`build_location_csv_from_bundles` reads the LOCA group of every
bundle and stamps the row.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import pandas as pd

from geoview_cpt.ags_convert.wrapper import AgsConvertError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = [
    "LOCATION_COLUMNS",
    "build_location_csv",
    "build_location_csv_from_bundles",
]


LOCATION_COLUMNS: tuple[str, ...] = (
    "LOCA_ID",
    "Easting",
    "Northing",
    "CRS",
    "GL_m",
    "Seabed_m",
    "Water_Depth_m",
    "Type",
    "Date",
    "Remarks",
)


def build_location_csv(
    rows: Iterable[dict[str, str]],
    path: str | Path,
) -> Path:
    """
    Write a project-wide location CSV from pre-built row dicts.

    Args:
        rows: iterable of dicts keyed by :data:`LOCATION_COLUMNS`.
              Missing keys yield empty cells.
        path: output path (parent dirs auto-created).

    Returns:
        Resolved output path. Always emits the header row even when
        the input is empty.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=list(LOCATION_COLUMNS),
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: str(row.get(k, "")) for k in LOCATION_COLUMNS})
    return path


def build_location_csv_from_bundles(
    bundles: Iterable["AGSBundle"],
    path: str | Path,
) -> Path:
    """
    Convenience: read each bundle's LOCA group and emit the project
    location CSV. Bundles with no LOCA group are skipped silently
    (the manifest can record the absence).
    """
    rows: list[dict[str, str]] = []
    for bundle in bundles:
        loca_df = bundle.tables.get("LOCA")
        if loca_df is None or len(loca_df) <= 2:
            continue
        rows.extend(_loca_rows(loca_df))
    return build_location_csv(rows, path)


def _loca_rows(loca_df: pd.DataFrame) -> list[dict[str, str]]:
    """Translate the AGS4 LOCA group into Kingdom location rows."""
    out: list[dict[str, str]] = []
    data = loca_df.iloc[2:]
    for _, raw in data.iterrows():
        out.append(
            {
                "LOCA_ID":       str(raw.get("LOCA_ID", "")).strip(),
                "Easting":       str(raw.get("LOCA_NATE", "")).strip(),
                "Northing":      str(raw.get("LOCA_NATN", "")).strip(),
                "CRS":           str(raw.get("LOCA_GREF", "")).strip(),
                "GL_m":          str(raw.get("LOCA_GL", "")).strip(),
                "Seabed_m":      str(raw.get("LOCA_GL", "")).strip(),
                "Water_Depth_m": str(raw.get("LOCA_FDEP", "")).strip(),
                "Type":          str(raw.get("LOCA_TYPE", "")).strip(),
                "Date":          str(raw.get("LOCA_STAR", "")).strip(),
                "Remarks":       str(raw.get("LOCA_PURP", "")).strip(),
            }
        )
    return out
