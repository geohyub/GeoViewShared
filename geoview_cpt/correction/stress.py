"""
geoview_cpt.correction.stress
================================
Total + effective vertical stress profiles.

Total stress at depth ``z``::

    σ_v0(z) = ∫₀ᶻ γ(s) ds

implemented as a trapezoidal cumulative sum because real CPT depth
samples are quasi-uniform but not perfectly equal. Effective stress is
the elementwise difference ``σ'_v0 = σ_v0 − u₀``.

Both routines accept a constant unit weight (single float) or a
:class:`CPTChannel` of γ samples — useful when γ varies with depth via
:func:`geoview_cpt.derivation.gamma.estimate_gamma`.
"""
from __future__ import annotations

from typing import Union

import numpy as np

from geoview_cpt.model import CPTChannel

__all__ = ["compute_sigma_v0", "compute_sigma_prime_v0"]


def _gamma_array(gamma: Union[float, CPTChannel], n: int) -> np.ndarray:
    if isinstance(gamma, CPTChannel):
        if gamma.values.shape != (n,):
            raise ValueError(
                f"gamma channel shape {gamma.values.shape} != depth length ({n},)"
            )
        return gamma.values
    if isinstance(gamma, (int, float)):
        if gamma <= 0:
            raise ValueError(f"gamma scalar must be positive, got {gamma}")
        return np.full(n, float(gamma))
    raise TypeError(
        f"gamma must be float or CPTChannel, got {type(gamma).__name__}"
    )


def compute_sigma_v0(
    depth: CPTChannel,
    gamma: Union[float, CPTChannel],
) -> CPTChannel:
    """
    Trapezoidal cumulative integration of γ × dz.

    Returns a ``"sigma_v0"`` channel in ``"kPa"`` (since 1 kN/m³ × 1 m = 1 kPa).
    """
    z = depth.values
    n = z.shape[0]
    if n == 0:
        return CPTChannel(name="sigma_v0", unit="kPa", values=np.empty(0))
    g = _gamma_array(gamma, n)

    # Trapezoidal slabs between consecutive samples; sigma at sample k is the
    # accumulated stress down to z[k]. Use prepend=z[0] so the very first
    # slab is non-negative even when z[0] > 0 (assume γ above the first
    # sample equals γ[0]).
    z_prev = np.concatenate(([z[0]], z[:-1]))
    g_prev = np.concatenate(([g[0]], g[:-1]))
    dz = z - z_prev
    avg_g = 0.5 * (g + g_prev)
    slabs = avg_g * dz
    sigma = np.cumsum(slabs)
    # Add a baseline contribution from surface (0) down to z[0] using g[0].
    if z[0] > 0:
        sigma += g[0] * z[0]
    return CPTChannel(name="sigma_v0", unit="kPa", values=sigma)


def compute_sigma_prime_v0(
    sigma_v0: CPTChannel,
    u0: CPTChannel,
) -> CPTChannel:
    """Elementwise σ'_v0 = σ_v0 − u₀ (both kPa)."""
    if sigma_v0.values.shape != u0.values.shape:
        raise ValueError(
            f"sigma_v0 / u0 shape mismatch: "
            f"{sigma_v0.values.shape} vs {u0.values.shape}"
        )
    return CPTChannel(
        name="sigma_prime_v0",
        unit="kPa",
        values=sigma_v0.values - u0.values,
    )
