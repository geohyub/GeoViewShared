"""
geoview_cpt.stratigraphy
================================
Auto-layering + manual edit helpers for CPT soundings (A2.8).

Public API:

    auto_split_by_ic        Robertson Ic threshold-based layering
    StratumEditor           mutable wrapper with move/merge/split ops
"""
from __future__ import annotations

from geoview_cpt.stratigraphy.ic_split import (
    DEFAULT_IC_THRESHOLDS,
    IcMode,
    StratumEditor,
    auto_split_by_ic,
)

__all__ = [
    "DEFAULT_IC_THRESHOLDS",
    "IcMode",
    "auto_split_by_ic",
    "StratumEditor",
]
