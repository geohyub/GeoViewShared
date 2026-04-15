"""
geoview_cpt.charts.dr_profile
================================
Relative density ``Dr`` vs depth.

Background is colored by the five Robertson 1990 / SPT N-derived
density classes (Very Loose → Very Dense, thresholds from
:mod:`geoview_gi.classification`) so the viewer reads the class label
without a separate key. Dr ratio from
:func:`geoview_cpt.derivation.strength.compute_dr_jamiolkowski` is
converted to percent for display.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from geoview_cpt.charts._helpers import depth_array, format_depth_axis
from geoview_cpt.derivation.strength import compute_dr_jamiolkowski
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from matplotlib.figure import Figure

__all__ = ["build_dr_profile"]


_DENSITY_BANDS: list[tuple[float, float, str, str]] = [
    # (dr_lo_pct, dr_hi_pct, label, fill)
    (0,   15, "Very Loose",   "#F4DDDE"),
    (15,  35, "Loose",        "#F4C4A1"),
    (35,  65, "Medium Dense", "#FFE4B5"),
    (65,  85, "Dense",        "#C6E2C3"),
    (85, 100, "Very Dense",   "#7FB084"),
]


def build_dr_profile(
    sounding: CPTSounding,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (5.0, 11.0),
) -> "Figure":
    """
    Plot Dr (%) vs depth.

    Requires raw ``qc`` (MPa) and derived ``sigma_prime_v0`` (kPa).
    Jamiolkowski's hardcoded-unit constraint is preserved by
    :func:`compute_dr_jamiolkowski`, so the builder fails fast if
    either channel carries the wrong unit.
    """
    import matplotlib.pyplot as plt

    qc = sounding.channels.get("qc")
    spv0 = sounding.derived.get("sigma_prime_v0")
    if qc is None or spv0 is None:
        raise KeyError(
            "build_dr_profile requires raw 'qc' and derived 'sigma_prime_v0'"
        )

    dr = compute_dr_jamiolkowski(qc, spv0)
    dr_pct = dr.values * 100.0
    depth = depth_array(sounding)

    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    ax.set_title(title or f"Dr profile · {sounding.name}")
    ax.set_xlabel("Relative density Dr (%)")
    ax.set_xlim(0, 100)
    ax.set_ylim(depth.max(), 0)

    for lo, hi, _label, fill in _DENSITY_BANDS:
        ax.axvspan(lo, hi, color=fill, alpha=0.25, zorder=0)

    ax.plot(dr_pct, depth, color="#0B2545", linewidth=1.0, zorder=3)

    for lo, _hi, label, _fill in _DENSITY_BANDS:
        ax.text(
            lo + 1, depth.max() * 0.02, label,
            fontsize=7, color="#1A1C1E", alpha=0.75,
            rotation=90, va="bottom", ha="left",
        )

    format_depth_axis(ax, invert=False)
    return fig
