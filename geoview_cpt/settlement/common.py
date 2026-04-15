"""
geoview_cpt.settlement.common
================================
Dataclasses shared across the settlement estimators.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["FoundationLoad", "SettlementResult"]


@dataclass(frozen=True)
class FoundationLoad:
    """
    Design foundation load — the standard set of inputs every settlement
    method needs.

    Attributes:
        net_bearing_kpa:  net applied pressure at foundation base (kPa).
        width_m:          foundation width B (m) — used by Schmertmann
                          influence-factor integration.
        length_m:         foundation length L (m). Defaults to
                          ``width_m`` (square footing).
        depth_m:          founding depth below ground surface (m).
        shape:            free-form shape label for reporting.
    """

    net_bearing_kpa: float
    width_m: float
    length_m: float = 0.0
    depth_m: float = 0.0
    shape: str = "square"

    def __post_init__(self) -> None:
        if self.net_bearing_kpa <= 0:
            raise ValueError("net_bearing_kpa must be positive")
        if self.width_m <= 0:
            raise ValueError("width_m must be positive")
        if self.depth_m < 0:
            raise ValueError("depth_m must be non-negative")
        if self.length_m == 0.0:
            object.__setattr__(self, "length_m", self.width_m)
        if self.length_m < self.width_m:
            raise ValueError("length_m must be ≥ width_m (L ≥ B)")


@dataclass
class SettlementResult:
    """
    Total + per-layer settlement breakdown from one method.

    Attributes:
        total_mm:      sum of ``per_layer_mm``.
        per_layer_mm:  contribution of each sublayer (length matches
                       ``depth_m``).
        depth_m:       depth vector defining the sublayer tops (same
                       length as ``per_layer_mm``).
        method:        identifier of the method used.
        extras:        free-form dict for diagnostic values (Iz, E, …).
    """

    total_mm: float
    per_layer_mm: np.ndarray
    depth_m: np.ndarray
    method: str
    extras: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return int(self.depth_m.shape[0])
