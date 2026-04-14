"""
geoview_cpt.derivation.sbt
================================
Robertson 1990 Soil Behaviour Type — Ic-based 9-zone classification.

The original Robertson 1990 chart partitions ``Qtn × Fr`` space; the
1998 update added the SBT Index ``Ic`` so a single 1-D ``Ic`` value maps
to a zone via fixed thresholds. We use the Ic mapping for the deriver
because it is the standard for downstream programmatic use (Lunne,
Robertson & Powell 1997 §5; Robertson 2009).

Zone reference:

    1  Sensitive fine grained
    2  Organic soils — clay
    3  Clays — silty clay to clay
    4  Silt mixtures — clayey silt to silty clay
    5  Sand mixtures — silty sand to sandy silt
    6  Sands — clean sand to silty sand
    7  Gravelly sand to dense sand
    8  Very stiff sand to clayey sand          (SBT chart only — not Ic-mappable)
    9  Very stiff fine grained                 (SBT chart only — not Ic-mappable)

Zones 8 and 9 require Qtn-Fr space inspection; the Ic deriver returns
zones 2..7 only. The full 9-zone chart classifier is reserved for
A2.7a charts.
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.model import CPTChannel

__all__ = [
    "ROBERTSON_1990_ZONES",
    "classify_ic_to_robertson_1990_zone",
    "classify_robertson_1990",
]


ROBERTSON_1990_ZONES: dict[int, str] = {
    1: "Sensitive fine grained",
    2: "Organic soils - clay",
    3: "Clays - silty clay to clay",
    4: "Silt mixtures - clayey silt to silty clay",
    5: "Sand mixtures - silty sand to sandy silt",
    6: "Sands - clean sand to silty sand",
    7: "Gravelly sand to dense sand",
    8: "Very stiff sand to clayey sand",
    9: "Very stiff fine grained",
}


# Ic boundaries from Robertson 2009 / Robertson & Wride 1998. The mapping
# is inclusive of the lower bound and exclusive of the upper:
_IC_BOUNDARIES: list[tuple[float, float, int]] = [
    (-np.inf, 1.31, 7),    # gravelly sand
    (1.31,    2.05, 6),    # clean sand
    (2.05,    2.60, 5),    # silty sand
    (2.60,    2.95, 4),    # clayey silt
    (2.95,    3.60, 3),    # clay
    (3.60,    np.inf, 2),  # organic clay
]


def classify_ic_to_robertson_1990_zone(ic_value: float) -> int:
    """Map a single Ic float to a Robertson 1990 zone (2..7)."""
    if not np.isfinite(ic_value):
        return 0
    for lo, hi, zone in _IC_BOUNDARIES:
        if lo <= ic_value < hi:
            return zone
    return 0


def classify_robertson_1990(ic: CPTChannel) -> CPTChannel:
    """
    Vectorized Ic → zone mapping. Returns a ``"SBT"`` channel of integer
    zones in the range 2..7. Non-finite Ic values map to 0.
    """
    arr = ic.values
    out = np.zeros(arr.shape, dtype=np.float64)
    finite = np.isfinite(arr)
    # Initialize valid samples to zone 2 (the highest-Ic / lowest-zone bin)
    out[finite] = 2
    out[finite & (arr < 3.60)] = 3
    out[finite & (arr < 2.95)] = 4
    out[finite & (arr < 2.60)] = 5
    out[finite & (arr < 2.05)] = 6
    out[finite & (arr < 1.31)] = 7
    return CPTChannel(name="SBT", unit="zone", values=out)
