"""
geoview_cpt.charts.su_profile
================================
Undrained shear strength ``Su`` vs depth, with multi-``Nkt`` support.

Default Wave 0 convention plots two curves — ``Nkt=15`` (lower bound)
and ``Nkt=30`` (upper bound) — so a reviewer can see the envelope.
Lab-measured Su points from :class:`geoview_gi.minimal_model.LabSample`
can be overlaid via the optional ``lab_samples`` argument.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import numpy as np

from geoview_cpt.charts._helpers import depth_array, format_depth_axis
from geoview_cpt.derivation.strength import DEFAULT_NKT, compute_su
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from geoview_gi.minimal_model import LabSample

__all__ = ["build_su_profile"]


_NKT_COLORS = ["#0B2545", "#C0392B", "#2E8B57", "#1E88E5", "#E09F3E"]


def build_su_profile(
    sounding: CPTSounding,
    *,
    nkt: float | Iterable[float] = DEFAULT_NKT,
    lab_samples: "Iterable[LabSample] | None" = None,
    title: str | None = None,
    figsize: tuple[float, float] = (6.0, 11.0),
) -> "Figure":
    """
    Render Su vs depth for one or more ``Nkt`` values.

    Args:
        sounding:   must have ``qt`` and ``sigma_v0`` on ``derived``.
        nkt:        single value or iterable; each produces a curve.
        lab_samples: optional lab Su points to overlay (scatter).
        title:      figure title; defaults to ``"Su profile · <name>"``.
    """
    import matplotlib.pyplot as plt

    qt = sounding.derived.get("qt") or sounding.channels.get("qt")
    sv0 = sounding.derived.get("sigma_v0") or sounding.channels.get("sigma_v0")
    if qt is None or sv0 is None:
        raise KeyError(
            "build_su_profile requires derived 'qt' and 'sigma_v0' channels"
        )

    if isinstance(nkt, (int, float)):
        nkt_iter: list[float] = [float(nkt)]
    else:
        nkt_iter = [float(n) for n in nkt]

    su_map = compute_su(qt, sv0, nkt=nkt_iter)
    depth = depth_array(sounding)

    fig, ax = plt.subplots(figsize=figsize, constrained_layout=True)
    ax.set_title(title or f"Su profile · {sounding.name}")
    ax.set_xlabel("Undrained shear strength Su (kPa)")

    for i, (n, channel) in enumerate(su_map.items()):
        ax.plot(
            channel.values, depth,
            color=_NKT_COLORS[i % len(_NKT_COLORS)],
            linewidth=1.1,
            label=f"Nkt = {int(n) if n == int(n) else n}",
        )

    if lab_samples is not None:
        lab_depths = []
        lab_values = []
        for s in lab_samples:
            if s.undrained_shear_strength_kpa is None:
                continue
            lab_depths.append(s.top_m)
            lab_values.append(s.undrained_shear_strength_kpa)
        if lab_depths:
            ax.scatter(
                lab_values, lab_depths,
                color="#1A1C1E", s=30, marker="D",
                label="Lab Su", zorder=4,
            )

    ax.set_xlim(left=0)
    format_depth_axis(ax)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    return fig
