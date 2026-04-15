"""
geoview_cpt.settlement
================================
1-D settlement estimators (Phase A-2 A2.12).

Two methods ship in v1:

    mayne_1d        Mayne 1-D elastic compression (PMT/CPT elastic
                    modulus integration)
    schmertmann     Schmertmann 1970 / 1978 influence-factor method

Both consume a :class:`FoundationLoad` and a depth-dependent elastic
modulus profile (or a per-layer constant when the caller already has
synthesized layer properties).
"""
from __future__ import annotations

from geoview_cpt.settlement.common import FoundationLoad, SettlementResult
from geoview_cpt.settlement.mayne_1d import mayne_1d_settlement
from geoview_cpt.settlement.schmertmann import schmertmann_settlement

__all__ = [
    "FoundationLoad",
    "SettlementResult",
    "mayne_1d_settlement",
    "schmertmann_settlement",
]
