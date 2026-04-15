"""
geoview_cpt.charts.cpet_it_compat
========================================
★ GeoView rev7 Annex 5 — CPeT-IT v.3.9.1.3 layout reproduction.

The rev7 Korean deliverable (``야월해상풍력_rev7_부록5_CPT성과``) is a
direct PDF export from CPeT-IT. When ``A2.0`` reads a ``.cpt`` project
authored by GeoView, the ``<Various>`` block still carries the Geoview
branding (``Marine Research Geotechnical Engineers``, Busan) — we can
therefore reproduce the same report layout from a :class:`CPTSounding`
without launching CPeT-IT at all.

Layout:

    ┌──────────────────────────────────────────────────────────────┐
    │ [logo?]    GEOVIEW — Marine Research Geotechnical Engineers   │
    │            Busan, South Korea  ·  http://www.geoview.co.kr    │
    │                                                               │
    │                Project: {name}    Sounding: {id}              │
    ├──────────────────────────────────────────────────────────────┤
    │ qc (MPa)          │ fs (kPa)        │ u₂ (kPa)                │
    │ 0..80             │ 0..200          │ ±2000                    │
    │                                                               │
    │  [curve]          │ [curve]         │ [curve]                  │
    │                                                               │
    │ Depth (m)         │ Depth (m)       │ Depth (m)                │
    ├──────────────────────────────────────────────────────────────┤
    │ Cross correlation — qc vs fs (log–log)                        │
    └──────────────────────────────────────────────────────────────┘
    geoview_cpt vX.Y.Z — CPeT-IT v.3.9.1.3 compatible

The footer is deliberately version-stamped so a reader of the PDF can
trace it back to a specific build.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from geoview_cpt.charts._helpers import (
    branding_footer,
    depth_array,
    get_raw,
    to_kpa_array,
    to_mpa_array,
)
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from geoview_cpt.model import CPTProject

__all__ = ["build_cpet_it_compat_plot"]


_TRACK_RANGES = {
    "qc": (0, 80),
    "fs": (0, 200),
    "u2": (-2000, 2000),
}

_TRACK_COLORS = {
    "qc": "#0B2545",
    "fs": "#C0392B",
    "u2": "#2E8B57",
}


def build_cpet_it_compat_plot(
    sounding: CPTSounding,
    *,
    project: "CPTProject | None" = None,
    title: str | None = None,
    figsize: tuple[float, float] = (8.27, 11.69),   # A4 portrait
) -> "Figure":
    """
    Render the rev7 Annex 5 CPeT-IT-compatible layout.

    Args:
        sounding: :class:`CPTSounding` with ``depth``, ``qc``, ``fs``,
                  ``u2`` raw channels.
        project:  optional :class:`CPTProject` providing branding 4
                  fields (``partner_brand / _description / _address /
                  _url``). When omitted we fall back to Wave 0 defaults.
        title:    free-form title override.

    Returns:
        matplotlib ``Figure`` sized for A4 portrait so the deliverable
        pack can drop it straight into a Word document.
    """
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt

    depth = depth_array(sounding)
    qc = to_mpa_array(get_raw(sounding, "qc"))
    fs = to_kpa_array(get_raw(sounding, "fs"))
    u2 = to_kpa_array(get_raw(sounding, "u2"))

    fig = plt.figure(figsize=figsize, constrained_layout=False)
    gs = gridspec.GridSpec(
        4, 3,
        height_ratios=[1.3, 10.0, 3.0, 0.3],
        hspace=0.35,
        wspace=0.25,
        left=0.10,
        right=0.97,
        top=0.96,
        bottom=0.04,
    )

    _draw_header(fig, gs[0, :], sounding, project, title)

    qc_ax = fig.add_subplot(gs[1, 0])
    fs_ax = fig.add_subplot(gs[1, 1], sharey=qc_ax)
    u2_ax = fig.add_subplot(gs[1, 2], sharey=qc_ax)

    _draw_track(qc_ax, qc, depth, "qc")
    _draw_track(fs_ax, fs, depth, "fs")
    _draw_track(u2_ax, u2, depth, "u2")

    qc_ax.set_ylabel("Depth (m)")
    qc_ax.invert_yaxis()

    corr_ax = fig.add_subplot(gs[2, :])
    _draw_cross_correlation(corr_ax, qc, fs)

    footer_ax = fig.add_subplot(gs[3, :])
    _draw_footer(footer_ax, sounding, project)

    return fig


# ---------------------------------------------------------------------------
# panel helpers
# ---------------------------------------------------------------------------


def _draw_header(fig, gs_cell, sounding, project, title_override) -> None:
    ax = fig.add_subplot(gs_cell)
    ax.axis("off")

    brand = project.partner_brand if project else "Geoview"
    description = (
        project.partner_description if project else "Marine Research Geotechnical Engineers"
    )
    address = project.partner_address if project else "Busan, South Korea"
    url = project.partner_url if project else "http://www.geoview.co.kr"
    project_name = (project.name if project else "").strip()

    title = title_override or f"CPT: {sounding.name}"

    ax.text(
        0.0, 0.85, brand.upper(),
        fontsize=14, fontweight="bold", color="#0B2545",
        transform=ax.transAxes,
    )
    ax.text(
        0.0, 0.58, description,
        fontsize=9, color="#1A1C1E",
        transform=ax.transAxes,
    )
    ax.text(
        0.0, 0.38, address,
        fontsize=9, color="#7A8089",
        transform=ax.transAxes,
    )
    ax.text(
        0.0, 0.18, url,
        fontsize=9, color="#1E88E5",
        transform=ax.transAxes,
    )

    ax.text(
        1.0, 0.85, title,
        fontsize=12, fontweight="bold", color="#0B2545",
        ha="right",
        transform=ax.transAxes,
    )
    if project_name:
        ax.text(
            1.0, 0.58, f"Project: {project_name}",
            fontsize=9, color="#1A1C1E",
            ha="right",
            transform=ax.transAxes,
        )
    ax.text(
        1.0, 0.38, f"Total depth: {float(np.nanmax(sounding.channels['depth'].values)):.2f} m",
        fontsize=9, color="#1A1C1E",
        ha="right",
        transform=ax.transAxes,
    )
    ax.text(
        1.0, 0.18, "Piezocone 15 cm² — CPeT-IT v.3.9.1.3 compatible",
        fontsize=8, color="#7A8089",
        ha="right",
        transform=ax.transAxes,
    )

    # Thin divider line underneath
    ax.axhline(0.0, color="#CBD5E0", linewidth=0.8)


def _draw_track(ax, values, depth, key) -> None:
    lo, hi = _TRACK_RANGES[key]
    color = _TRACK_COLORS[key]
    ax.plot(values, depth, color=color, linewidth=0.9)
    ax.set_xlim(lo, hi)
    ax.set_title({"qc": "Cone resistance qc (MPa)",
                  "fs": "Sleeve friction fs (kPa)",
                  "u2": "Pore pressure u₂ (kPa)"}[key],
                 fontsize=10)
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
    ax.tick_params(labelsize=8)


def _draw_cross_correlation(ax, qc: np.ndarray, fs: np.ndarray) -> None:
    """Scatter qc×fs (MPa, kPa) with a loose trend line."""
    mask = np.isfinite(qc) & np.isfinite(fs) & (qc > 0) & (fs > 0)
    if mask.any():
        qc_f = qc[mask]
        fs_f = fs[mask]
        if qc_f.size > 1500:
            stride = qc_f.size // 1500
            qc_f = qc_f[::stride]
            fs_f = fs_f[::stride]
        ax.scatter(qc_f, fs_f, s=4, c="#0B2545", alpha=0.45, edgecolor="none")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("qc (MPa)", fontsize=9)
    ax.set_ylabel("fs (kPa)", fontsize=9)
    ax.set_title("Cross correlation — qc vs fs", fontsize=10)
    ax.grid(True, which="both", linestyle=":", linewidth=0.5, alpha=0.5)
    ax.tick_params(labelsize=8)


def _draw_footer(ax, sounding, project) -> None:
    ax.axis("off")
    project_name = (project.name if project else sounding.name)
    brand = project.partner_brand if project else "Geoview"
    url = project.partner_url if project else "http://www.geoview.co.kr"
    ax.text(
        0.0, 0.5,
        branding_footer(project_name, partner_brand=brand, partner_url=url),
        fontsize=7,
        color="#7A8089",
        transform=ax.transAxes,
    )
    ax.text(
        1.0, 0.5,
        "geoview_cpt A2.7b — CPeT-IT v.3.9.1.3 compatible",
        fontsize=7,
        color="#7A8089",
        ha="right",
        transform=ax.transAxes,
    )
