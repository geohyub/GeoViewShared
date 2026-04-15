"""
geoview_cpt.charts.ic_profile
================================
Robertson Soil Behavior Type Index vs depth.

Simple single-panel plot: ``Ic`` on x, depth on y (inverted so deeper
samples are lower). The background is colored by the 6 Ic-thresholded
zones (2..7) so a reader can eyeball the stratigraphy without
consulting the full SBT chart.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from geoview_cpt.charts._helpers import (
    depth_array,
    format_depth_axis,
    get_either,
)
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from matplotlib.figure import Figure

__all__ = ["build_ic_profile"]


# Ic threshold → zone (Robertson 2009) + background color
_IC_BANDS: list[tuple[float, float, str, str]] = [
    # (ic_lo, ic_hi, label, fill)
    (0.00, 1.31, "Zone 7 — Gravelly sand",  "#F4B000"),
    (1.31, 2.05, "Zone 6 — Clean sand",     "#FFD57F"),
    (2.05, 2.60, "Zone 5 — Silty sand",     "#FFE4B5"),
    (2.60, 2.95, "Zone 4 — Clayey silt",    "#9CC2E5"),
    (2.95, 3.60, "Zone 3 — Clay",           "#7FB0DB"),
    (3.60, 5.00, "Zone 2 — Organic clay",   "#6299C9"),
]


def build_ic_profile(
    sounding: CPTSounding,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (5.0, 11.0),
) -> "Figure":
    """
    Plot Ic vs depth with zone-colored background bands.

    Requires ``Ic`` on ``sounding.derived`` (or ``sounding.channels``).
    """
    import matplotlib.pyplot as plt

    ic = get_either(sounding, "Ic").values
    depth = depth_array(sounding)

    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    ax.set_title(title or f"Ic profile · {sounding.name}")
    ax.set_xlabel("Soil Behavior Type Index Ic")
    ax.set_xlim(1.0, 4.5)
    ax.set_ylim(depth.max(), 0)   # inverted in data coords so bands work

    for ic_lo, ic_hi, _label, fill in _IC_BANDS:
        ax.axvspan(ic_lo, ic_hi, color=fill, alpha=0.25, zorder=0)

    ax.plot(ic, depth, color="#0B2545", linewidth=1.0, zorder=3)
    format_depth_axis(ax, invert=False)

    # Legend strip along the top for the zone labels
    for ic_lo, _ic_hi, label, fill in _IC_BANDS:
        ax.text(
            ic_lo + 0.02, depth.max() * 0.02, label,
            fontsize=7, color="#1A1C1E", alpha=0.75,
            rotation=90, va="bottom", ha="left",
        )

    return fig
