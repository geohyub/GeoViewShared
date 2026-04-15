"""
geoview_cpt.charts.log_plot
================================
HELMS Appendix B 5-track CPT log plot.

Layout:

    ┌─────────┬─────────┬─────────┬─────────┬─────────┐
    │  qc     │  fs     │  u₂     │  Rf     │  Bq     │
    │  (MPa)  │  (kPa)  │  (kPa)  │  (%)    │  (−)    │
    │         │         │         │         │         │
    │  depth  │  depth  │  depth  │  depth  │  depth  │
    │  (m)    │  (m)    │  (m)    │  (m)    │  (m)    │
    └─────────┴─────────┴─────────┴─────────┴─────────┘

Raw channels (``qc``, ``fs``, ``u2``) are required; derived channels
(``Rf``, ``Bq``) are optional — missing tracks render an empty axis
with a "data not computed" note so callers can pass a sounding that
has not yet been through :mod:`geoview_cpt.derivation` without the
builder crashing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from geoview_cpt.charts._helpers import (
    MissingChannelError,
    depth_array,
    format_depth_axis,
    get_either,
    get_raw,
    to_kpa_array,
    to_mpa_array,
)
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from matplotlib.figure import Figure

__all__ = ["build_log_plot"]


_TRACK_STYLE = {
    "qc": {"color": "#0B2545", "label": "qc (MPa)", "xlim": None},
    "fs": {"color": "#C0392B", "label": "fs (kPa)", "xlim": None},
    "u2": {"color": "#2E8B57", "label": "u₂ (kPa)", "xlim": None},
    "Rf": {"color": "#E09F3E", "label": "Rf (%)", "xlim": (0, 10)},
    "Bq": {"color": "#1E88E5", "label": "Bq (−)", "xlim": (-0.5, 1.5)},
}


def build_log_plot(
    sounding: CPTSounding,
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (11.0, 14.0),
) -> "Figure":
    """
    Render a 5-track HELMS-style log plot for ``sounding``.

    Args:
        sounding: :class:`CPTSounding` with at least ``depth``, ``qc``,
                  ``fs``, ``u2`` raw channels. ``Rf`` and ``Bq`` come
                  from ``sounding.derived`` and are optional.
        title:    figure title; defaults to ``sounding.name``.
        figsize:  matplotlib figsize tuple.

    Returns:
        matplotlib ``Figure`` with 5 :class:`~matplotlib.axes.Axes`
        stored as ``fig.axes[0..4]``.
    """
    import matplotlib.pyplot as plt

    depth = depth_array(sounding)
    try:
        qc = to_mpa_array(get_raw(sounding, "qc"))
    except MissingChannelError:
        qc = None
    try:
        fs = to_kpa_array(get_raw(sounding, "fs"))
    except MissingChannelError:
        fs = None
    try:
        u2 = to_kpa_array(get_raw(sounding, "u2"))
    except MissingChannelError:
        u2 = None
    try:
        rf = get_either(sounding, "Rf").values
    except MissingChannelError:
        rf = None
    try:
        bq = get_either(sounding, "Bq").values
    except MissingChannelError:
        bq = None

    fig, axes = plt.subplots(
        1, 5, figsize=figsize, sharey=True, constrained_layout=True
    )
    fig.suptitle(title or f"CPT log · {sounding.name}", fontsize=13)

    _draw_track(axes[0], depth, qc, "qc")
    _draw_track(axes[1], depth, fs, "fs")
    _draw_track(axes[2], depth, u2, "u2")
    _draw_track(axes[3], depth, rf, "Rf")
    _draw_track(axes[4], depth, bq, "Bq")

    format_depth_axis(axes[0])
    for ax in axes[1:]:
        ax.invert_yaxis()
        ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.7)

    return fig


def _draw_track(ax, depth: np.ndarray, values, key: str) -> None:
    style = _TRACK_STYLE[key]
    ax.set_title(style["label"], fontsize=10)
    if values is None or len(values) == 0:
        ax.text(
            0.5, 0.5, "not computed",
            ha="center", va="center",
            transform=ax.transAxes,
            color="#7A8089", fontsize=9, style="italic",
        )
        ax.set_xticks([])
        return
    ax.plot(values, depth, color=style["color"], linewidth=0.9)
    if style["xlim"] is not None:
        ax.set_xlim(*style["xlim"])
    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
