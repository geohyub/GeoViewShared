"""
geoview_cpt.correction.qt
================================
Eq 1 — corrected cone resistance ``qt`` (Lunne et al. 1997).

    qt = qc + u₂ × (1 − a)

where ``a`` is the cone area ratio (200 mm² JAKO Korea = 0.7032,
1000 mm² HELMS = 0.71). Inputs may be in MPa or kPa — :func:`compute_qt`
routes them through :func:`geoview_cpt.correction.units.to_mpa` so
either ingest path produces an MPa output channel.
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.correction.units import to_mpa
from geoview_cpt.model import CPTChannel

__all__ = ["compute_qt"]


def compute_qt(qc: CPTChannel, u2: CPTChannel, a: float) -> CPTChannel:
    """
    Compute the corrected cone resistance channel.

    Args:
        qc:  raw measured cone resistance (MPa preferred, kPa accepted).
        u2:  measured pore pressure behind the shoulder (MPa or kPa).
        a:   cone area ratio (dimensionless, typically 0.5..1.0).

    Returns:
        :class:`CPTChannel` named ``"qt"`` with unit ``"MPa"``.

    Raises:
        ValueError:  on length mismatch, ``a`` out of range, or unknown
                     unit on either input channel.
    """
    if not 0.0 <= a <= 1.0:
        raise ValueError(f"cone area ratio a must be in [0, 1], got {a}")
    qc_mpa = to_mpa(qc)
    u2_mpa = to_mpa(u2)
    if qc_mpa.shape != u2_mpa.shape:
        raise ValueError(
            f"qc/u2 shape mismatch: {qc_mpa.shape} vs {u2_mpa.shape}"
        )
    qt = qc_mpa + u2_mpa * (1.0 - a)
    return CPTChannel(name="qt", unit="MPa", values=qt)
