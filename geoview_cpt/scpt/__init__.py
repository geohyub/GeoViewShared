"""
geoview_cpt.scpt
================================
Seismic CPT (SCPT) backend — Phase A-2 A2.14.

Pure-backend module: first-break auto-picking + pseudo / true
interval velocity computations. No UI — Phase B CPTProc adds the
interactive wiggle viewer + manual override point on top.

Public API:

    FirstBreakPick           frozen dataclass per trace
    pick_first_breaks        STA/LTA auto-picker over a seismogram set
    pseudo_interval_velocity one-receiver ray-path vs depth
    true_interval_velocity   pair-of-receivers ray-path difference
"""
from __future__ import annotations

from geoview_cpt.scpt.first_break_picking import (
    DEFAULT_LTA_WINDOW_MS,
    DEFAULT_STA_WINDOW_MS,
    DEFAULT_THRESHOLD,
    FirstBreakPick,
    pick_first_breaks,
    pseudo_interval_velocity,
    true_interval_velocity,
)

__all__ = [
    "FirstBreakPick",
    "DEFAULT_STA_WINDOW_MS",
    "DEFAULT_LTA_WINDOW_MS",
    "DEFAULT_THRESHOLD",
    "pick_first_breaks",
    "pseudo_interval_velocity",
    "true_interval_velocity",
]
