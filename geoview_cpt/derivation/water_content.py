"""
geoview_cpt.derivation.water_content
========================================
Water content helper — BS 1377-2 : 1990.

Not a CPT-derived channel per se (water content is a lab measurement
on recovered samples), but we keep the formula here so the Deliverables
Pack and lab-report writers pull it from the same place as the rest of
the geotechnical vocabulary.

    ω (%) = (m_w − m_d) / m_d × 100

where ``m_w`` is the wet-soil mass and ``m_d`` is the oven-dry mass.
Accepts scalars or numpy arrays; the output shape matches the input.
"""
from __future__ import annotations

from typing import Union

import numpy as np

__all__ = ["compute_water_content"]


Numeric = Union[float, np.ndarray]


def compute_water_content(mass_wet: Numeric, mass_dry: Numeric) -> Numeric:
    """
    BS 1377-2 Part 2 : 1990 § 3 — gravimetric water content.

    Args:
        mass_wet: wet-soil mass (scalar or array).
        mass_dry: oven-dry mass (scalar or array of matching shape).

    Returns:
        Water content in percent — scalar when both inputs are scalar,
        numpy array otherwise.

    Raises:
        ValueError: if any ``mass_dry`` value is non-positive or the
                    input shapes disagree.
    """
    w = np.asarray(mass_wet, dtype=np.float64)
    d = np.asarray(mass_dry, dtype=np.float64)
    if w.shape != d.shape:
        raise ValueError(f"mass shapes disagree: {w.shape} vs {d.shape}")
    if np.any(d <= 0):
        raise ValueError("mass_dry must be strictly positive")
    omega = (w - d) / d * 100.0
    # Preserve scalar-in / scalar-out ergonomics
    if omega.ndim == 0:
        return float(omega)
    return omega
