"""
geoview_cpt.correction.u0
================================
Hydrostatic pore-pressure profile.

For marine CPT we measure depth from the seabed and assume the soil
above the groundwater table is dry (``GWT`` ≥ 0). At each depth ``z``::

    u₀(z) = γ_w × max(z − GWT, 0)

Default ``γ_w`` = 9.81 kN/m³ matches GeoView rev7 / HELMS conventions
(Wave 0 reconnaissance). For a CPT inside a borehole on land, callers
pass the actual GWT depth.
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.model import CPTChannel

__all__ = ["hydrostatic_pressure", "DEFAULT_GAMMA_W_KN_M3"]


DEFAULT_GAMMA_W_KN_M3: float = 9.81
"""Fresh / sea-water unit weight default for marine CPT (kN/m³)."""


def hydrostatic_pressure(
    depth: CPTChannel,
    *,
    gwt_m: float = 0.0,
    gamma_w: float = DEFAULT_GAMMA_W_KN_M3,
) -> CPTChannel:
    """
    Build the hydrostatic ``u₀`` profile (kPa).

    Args:
        depth:   ``"depth"`` channel in metres.
        gwt_m:   groundwater table depth below ground surface, in metres.
                 Defaults to 0 (seabed surface).
        gamma_w: water unit weight (kN/m³).

    Returns:
        :class:`CPTChannel` named ``"u0"`` with unit ``"kPa"``.
    """
    if gamma_w <= 0:
        raise ValueError(f"gamma_w must be positive, got {gamma_w}")
    z = depth.values
    head = np.maximum(z - gwt_m, 0.0)
    u0 = head * gamma_w  # kN/m² = kPa
    return CPTChannel(name="u0", unit="kPa", values=u0)
