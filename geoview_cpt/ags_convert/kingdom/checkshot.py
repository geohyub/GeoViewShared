"""
Kingdom checkshot CSV — Phase A-4 Week 17 A4.2.

Emits one CSV per CPT sounding pairing the depth/TWT first-break
picks (from the A-2 :mod:`geoview_cpt.scpt.first_break_picking`
module) with the interval / average shear-wave velocities. Kingdom
imports these as a velocity profile for the well-log section view
(``09_kingdom/checkshot/<LOCA_ID>.csv``).

Schema (Kingdom standard)::

    # CRS: <epsg>                 ← header comment, ignored by Kingdom parser
    Depth_m,TWT_ms,Interval_Vs_m_s,Average_Vs_m_s,Source_Offset_m,Quality_Flag
    1.50,12.34,180.0,180.0,1.0,A
    2.00,15.56,160.5,170.2,1.0,A
    ...

Velocities reuse the existing
``geoview_cpt.scpt.first_break_picking.true_interval_velocity`` and
``pseudo_interval_velocity`` helpers — **no recomputation in this
module** per the Week 17 spec. ``Interval_Vs`` is the true interval
velocity between consecutive picks (vertical assumption); when the
caller supplies a non-zero ``source_offset_m`` the writer falls back
to the straight-ray ``pseudo_interval_velocity``.

Soundings without picks are **skipped entirely** (no empty file
emitted) so the Week 18 manifest can list them with a ``reason:
no_seismic_picks`` entry without breaking the file count.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from geoview_cpt.scpt.first_break_picking import (
    FirstBreakPick,
    pseudo_interval_velocity,
    true_interval_velocity,
)

__all__ = [
    "CHECKSHOT_COLUMNS",
    "SCPTSoundingPicks",
    "build_checkshot_csv",
    "build_checkshot_directory",
]


CHECKSHOT_COLUMNS: tuple[str, ...] = (
    "Depth_m",
    "TWT_ms",
    "Interval_Vs_m_s",
    "Average_Vs_m_s",
    "Source_Offset_m",
    "Quality_Flag",
)


@dataclass
class SCPTSoundingPicks:
    """
    Container the checkshot writer expects per sounding.

    Attributes:
        loca_id:         AGS4 LOCA_ID for filename + CRS comment.
        picks:           ordered list of :class:`FirstBreakPick` —
                         shallow → deep. Empty list is allowed and
                         produces a skipped sounding.
        crs:             CRS string for the ``# CRS:`` comment.
        source_offset_m: horizontal source offset in metres. ``0.0``
                         (default) selects vertical-assumption
                         interval velocity; non-zero switches to the
                         straight-ray pseudo-interval velocity.
    """

    loca_id: str
    picks: Sequence[FirstBreakPick]
    crs: str = ""
    source_offset_m: float = 0.0


def build_checkshot_csv(
    sounding_picks: SCPTSoundingPicks,
    path: str | Path,
) -> Path | None:
    """
    Write the checkshot CSV for a single sounding.

    Returns:
        ``None`` when the sounding has no picks (caller should record
        the skip in the manifest). Otherwise the resolved output path.
    """
    if not sounding_picks.picks:
        return None

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = _build_rows(
        sounding_picks.picks,
        source_offset_m=sounding_picks.source_offset_m,
    )

    with path.open("w", encoding="utf-8", newline="") as fh:
        if sounding_picks.crs:
            fh.write(f"# CRS: {sounding_picks.crs}\n")
        writer = csv.writer(fh)
        writer.writerow(CHECKSHOT_COLUMNS)
        for row in rows:
            writer.writerow(row)
    return path


def build_checkshot_directory(
    sounding_picks: Iterable[SCPTSoundingPicks],
    directory: str | Path,
) -> dict[str, Path | None]:
    """
    Write a checkshot CSV per sounding into ``directory``.

    Returns a mapping ``loca_id → path`` so the Week 18 manifest can
    record file names alongside skip reasons (``None`` for the
    skipped soundings).
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path | None] = {}
    for record in sounding_picks:
        target = directory / f"{record.loca_id}.csv"
        out[record.loca_id] = build_checkshot_csv(record, target)
    return out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _build_rows(
    picks: Sequence[FirstBreakPick],
    *,
    source_offset_m: float,
) -> list[list[str]]:
    """Render the per-pick rows with interval + cumulative average."""
    rows: list[list[str]] = []
    cumulative_distance = 0.0
    cumulative_time_s = 0.0
    prev: FirstBreakPick | None = None

    for pick in picks:
        depth = float(pick.depth_m)
        twt = float(pick.time_ms)

        if prev is None:
            interval = ""
            average = ""
        else:
            try:
                if source_offset_m > 0:
                    interval_v = pseudo_interval_velocity(
                        prev, pick, source_offset_x_m=source_offset_m
                    )
                else:
                    interval_v = true_interval_velocity(prev, pick)
                interval = f"{interval_v:.1f}"
            except (ValueError, ZeroDivisionError):
                interval = ""

            cumulative_distance += abs(depth - prev.depth_m)
            cumulative_time_s += max(0.0, (twt - prev.time_ms) / 1000.0)
            if cumulative_time_s > 0.0:
                average = f"{cumulative_distance / cumulative_time_s:.1f}"
            else:
                average = ""

        quality = _quality_flag(pick.confidence)
        rows.append(
            [
                f"{depth:.2f}",
                f"{twt:.2f}",
                interval,
                average,
                f"{source_offset_m:.1f}",
                quality,
            ]
        )
        prev = pick

    return rows


def _quality_flag(confidence: float) -> str:
    """Map the FirstBreakPick.confidence float to Kingdom A/B/C/D."""
    if not np.isfinite(confidence):
        return "D"
    if confidence >= 0.85:
        return "A"
    if confidence >= 0.65:
        return "B"
    if confidence >= 0.40:
        return "C"
    return "D"
