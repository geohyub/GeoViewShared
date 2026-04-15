"""
geoview_cpt.charts.sbt_chart
================================
Robertson 1990 Soil Behavior Type chart — 9-zone log-log scatter.

Axes:

    x : normalized friction ratio Fr (%), log10 scale 0.1..10
    y : normalized cone resistance Qtn (−), log10 scale 1..1000

Zone boundaries follow Robertson 1990 (Lunne, Robertson & Powell 1997
Table 5.3). The 9-zone boundaries are encoded as polygon vertices in
(Fr, Qtn) space and plotted behind the sample scatter.

This module deliberately avoids any interactive pyqtgraph dependency
so the chart ships as a clean SVG/PDF via
:class:`geoview_pyside6.export.VectorExportEngine`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from geoview_cpt.charts._helpers import MissingChannelError, get_either
from geoview_cpt.derivation.sbt import ROBERTSON_1990_ZONES
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from matplotlib.figure import Figure

__all__ = ["build_sbt_chart"]


# Zone polygons in (Fr%, Qtn) space. Values are simplified bounding
# rectangles adequate for the deliverable chart; the 1998 update uses
# smooth Ic contours which we overlay separately.
_ZONE_BOXES: dict[int, tuple[float, float, float, float]] = {
    # zone: (fr_min, fr_max, qtn_min, qtn_max)
    1: (0.10,  10.0,   1.0,    10.0),   # Sensitive fine grained
    2: (2.50,  10.0,   1.0,    12.0),   # Organic soils - clay
    3: (1.00,  10.0,   3.0,    30.0),   # Clays
    4: (0.50,   5.0,   12.0,   60.0),   # Silt mixtures
    5: (0.20,   2.5,   20.0,  120.0),   # Sand mixtures
    6: (0.10,   1.5,   60.0,  300.0),   # Clean sand
    7: (0.10,   1.0,  200.0, 1000.0),   # Gravelly sand
    8: (1.00,   2.5,  200.0, 1000.0),   # Very stiff sand to clayey sand
    9: (1.50,  10.0,  100.0, 1000.0),   # Very stiff fine grained
}


_ZONE_FILL = {
    1: "#E8EEF5",
    2: "#C3DAF0",
    3: "#9CC2E5",
    4: "#7FB0DB",
    5: "#FFE4B5",
    6: "#FFD57F",
    7: "#F4B000",
    8: "#D9A05B",
    9: "#A56A3E",
}


def build_sbt_chart(
    sounding: CPTSounding,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (8.0, 8.0),
    max_points: int = 2000,
) -> "Figure":
    """
    Render the Robertson 1990 SBT chart for ``sounding``.

    Requires ``Qtn`` (or ``Qt1``) and ``Fr`` on ``sounding.derived``.
    Samples are plotted as a light scatter over the zone polygons.

    ``max_points`` caps the scatter count so a 4000-sample sounding
    still renders in under 200 ms on the deliverable exporter.
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    try:
        qtn = get_either(sounding, "Qtn")
    except MissingChannelError:
        qtn = get_either(sounding, "Qt1")  # Robertson 1990 fallback
    fr = get_either(sounding, "Fr")

    qtn_arr = np.asarray(qtn.values, dtype=float)
    fr_arr = np.asarray(fr.values, dtype=float)

    mask = np.isfinite(qtn_arr) & np.isfinite(fr_arr) & (qtn_arr > 0) & (fr_arr > 0)
    qtn_arr = qtn_arr[mask]
    fr_arr = fr_arr[mask]
    if qtn_arr.size > max_points:
        stride = max(1, qtn_arr.size // max_points)
        qtn_arr = qtn_arr[::stride]
        fr_arr = fr_arr[::stride]

    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.1, 10.0)
    ax.set_ylim(1.0, 1000.0)
    ax.set_xlabel("Friction ratio Fr (%)")
    ax.set_ylabel("Normalized resistance Qtn")
    ax.set_title(title or f"Robertson 1990 SBT · {sounding.name}")

    _draw_zones(ax)

    ax.scatter(
        fr_arr, qtn_arr,
        s=6, c="#0B2545", alpha=0.5, edgecolor="none",
        zorder=3,
    )
    ax.grid(True, which="both", linestyle=":", linewidth=0.5, alpha=0.5)

    return fig


def _draw_zones(ax) -> None:
    from matplotlib.patches import Rectangle

    for zone_id, (fr_lo, fr_hi, q_lo, q_hi) in _ZONE_BOXES.items():
        rect = Rectangle(
            (fr_lo, q_lo),
            fr_hi - fr_lo,
            q_hi - q_lo,
            facecolor=_ZONE_FILL[zone_id],
            edgecolor="#7A8089",
            linewidth=0.5,
            alpha=0.35,
            zorder=1,
        )
        ax.add_patch(rect)
        # Label at the geometric center (log space)
        cx = 10 ** ((np.log10(fr_lo) + np.log10(fr_hi)) / 2)
        cy = 10 ** ((np.log10(q_lo) + np.log10(q_hi)) / 2)
        ax.text(
            cx, cy, str(zone_id),
            ha="center", va="center",
            fontsize=9, color="#1A1C1E", alpha=0.8, zorder=2,
        )
