"""
geoview_cpt.derivation.rf
================================
Eq 3 — friction ratio ``Rf`` (%).

    Rf = (fs / qt) × 100

Both inputs are converted to the same unit before division so the
parser-level "fs in kPa, qc in MPa" canonical layout doesn't leak into
the formula. ``qt`` near zero yields ``Rf = 0`` rather than NaN — the
0..first-sample noise band is meaningless and downstream chart code
expects finite values.
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.correction.units import to_kpa
from geoview_cpt.model import CPTChannel

__all__ = ["compute_rf"]


_QT_FLOOR_KPA = 1e-3   # below this, treat as zero to avoid Rf blow-up


def compute_rf(fs: CPTChannel, qt: CPTChannel) -> CPTChannel:
    """
    Compute friction ratio (%) channel.

    Args:
        fs: sleeve friction (MPa or kPa).
        qt: corrected cone resistance (MPa or kPa).

    Returns:
        :class:`CPTChannel` named ``"Rf"`` with unit ``"%"``.
    """
    fs_kpa = to_kpa(fs)
    qt_kpa = to_kpa(qt)
    if fs_kpa.shape != qt_kpa.shape:
        raise ValueError(
            f"fs/qt shape mismatch: {fs_kpa.shape} vs {qt_kpa.shape}"
        )
    rf = np.zeros_like(qt_kpa)
    valid = qt_kpa > _QT_FLOOR_KPA
    rf[valid] = (fs_kpa[valid] / qt_kpa[valid]) * 100.0
    return CPTChannel(name="Rf", unit="%", values=rf)
