"""
geoview_cpt.charts.borehole_log_kr
========================================
★ GeoView rev7 Annex 3 — Korean marine borehole log reproduction.

Departures from the HELMS Appendix B log (Wave 0 discovery):

 - **30 m per page** (HELMS uses 17 m), controlled via ``max_depth_per_page``
 - Track layout dedicated to the Korean deliverable:
     표고(GL elev) · 심도 · 층후 · 주상도(USCS hatch) · 층명 · 지층명(한글)
     기호 · 시료 · SPT N값 (scatter + curve)
 - **Pretendard Korean subset embed** — :mod:`geoview_pyside6.export.fonts`
   registers Pretendard Regular/Medium/SemiBold/Bold at import time, and
   matplotlib's ``svg.fonttype=none`` (A1.5 default) keeps Korean labels
   as ``<text>`` elements so downstream Acrobat / InDesign / Word can
   re-flow them without a missing-glyph box.
 - **GEOVIEW logo only** — rev7 Annex 3 does not repeat the client logo
   in the per-page header; the full page banner is reserved for the
   cover.

The builder accepts any :class:`CPTSounding` with strata and optional
SPT results attached via ``sounding.metadata['borehole']``. When the
sounding has no stratigraphy attached the chart renders the
qc-coloured "auto SBT" fallback so the page is not empty.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Sequence

import numpy as np

from geoview_cpt.charts._helpers import depth_array, format_depth_axis, get_raw, to_mpa_array
from geoview_cpt.model import CPTSounding

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from geoview_gi.minimal_model import Borehole, SPTTest, StratumLayer

__all__ = ["build_borehole_log_kr"]


_LEGEND_COLORS = {
    "SM": "#F4DDBE",  # silty sand
    "SP": "#FFE4B5",  # poorly graded sand
    "SC": "#E9C59B",  # clayey sand
    "CL": "#9CC2E5",  # lean clay
    "CH": "#5F8EC4",  # fat clay
    "ML": "#C3DAF0",  # silt
    "MH": "#7FB0DB",
    "GW": "#D9A05B",  # gravel
    "GC": "#B6742F",
    "ROCK": "#8B6E4E",
}


def build_borehole_log_kr(
    sounding: CPTSounding,
    *,
    strata: "Sequence[StratumLayer] | None" = None,
    spt_tests: "Iterable[SPTTest] | None" = None,
    project_name: str = "",
    borehole_id: str = "",
    page: int = 1,
    max_depth_per_page: float = 30.0,
    figsize: tuple[float, float] = (8.27, 11.69),  # A4 portrait
) -> "Figure":
    """
    Render one page of the Korean borehole log.

    Args:
        sounding:           :class:`CPTSounding` with ``depth`` and ``qc``.
        strata:             iterable of :class:`StratumLayer` — required
                            for the hatch/label tracks. When ``None``
                            we pull ``sounding.strata``.
        spt_tests:          iterable of :class:`SPTTest`. When ``None``
                            we pull ``sounding.metadata.get('spt', [])``.
        project_name:       shown in the header strip.
        borehole_id:        shown in the header strip.
        page:               1-based page index for the depth window.
        max_depth_per_page: metres per page (default 30 m — GeoView rev7).
        figsize:            matplotlib figsize (default A4 portrait).

    Returns:
        matplotlib ``Figure``. Use :class:`VectorExportEngine` for the
        SVG/PDF/PNG triple — the Korean labels ride along as ``<text>``
        nodes with Pretendard attribution.
    """
    import matplotlib.gridspec as gridspec
    import matplotlib.pyplot as plt

    if strata is None:
        strata = sounding.strata
    strata = list(strata) if strata is not None else []

    if spt_tests is None:
        spt_tests = sounding.metadata.get("spt") or ()
    spt_tests = list(spt_tests)

    depth_window = _depth_window_for_page(
        sounding=sounding,
        strata=strata,
        page=page,
        max_depth_per_page=max_depth_per_page,
    )

    fig = plt.figure(figsize=figsize, constrained_layout=False)
    gs = gridspec.GridSpec(
        3, 6,
        height_ratios=[1.2, 12.5, 0.5],
        width_ratios=[0.6, 0.6, 0.6, 2.8, 1.6, 2.0],
        hspace=0.2,
        wspace=0.1,
        left=0.07,
        right=0.97,
        top=0.96,
        bottom=0.03,
    )

    _draw_header(
        fig.add_subplot(gs[0, :]),
        project_name=project_name,
        borehole_id=borehole_id or sounding.name,
        page=page,
        depth_window=depth_window,
        max_depth_per_page=max_depth_per_page,
    )

    elev_ax = fig.add_subplot(gs[1, 0])
    depth_ax = fig.add_subplot(gs[1, 1], sharey=elev_ax)
    thick_ax = fig.add_subplot(gs[1, 2], sharey=elev_ax)
    column_ax = fig.add_subplot(gs[1, 3], sharey=elev_ax)
    name_ax = fig.add_subplot(gs[1, 4], sharey=elev_ax)
    spt_ax = fig.add_subplot(gs[1, 5], sharey=elev_ax)

    _draw_elev_track(elev_ax, depth_window, sounding)
    _draw_depth_track(depth_ax, depth_window)
    _draw_thickness_track(thick_ax, depth_window, strata)
    _draw_column_track(column_ax, depth_window, strata, sounding)
    _draw_name_track(name_ax, depth_window, strata)
    _draw_spt_track(spt_ax, depth_window, spt_tests)

    for ax in (elev_ax, depth_ax, thick_ax, column_ax, name_ax, spt_ax):
        ax.set_ylim(depth_window[1], depth_window[0])
        ax.tick_params(labelsize=7)

    footer_ax = fig.add_subplot(gs[2, :])
    _draw_footer(footer_ax, project_name, borehole_id or sounding.name, page)

    return fig


# ---------------------------------------------------------------------------
# paging
# ---------------------------------------------------------------------------


def _depth_window_for_page(
    *,
    sounding: CPTSounding,
    strata,
    page: int,
    max_depth_per_page: float,
) -> tuple[float, float]:
    if strata:
        z_max = max(s.base_m for s in strata)
    else:
        z_max = float(np.nanmax(sounding.channels["depth"].values))
    top = (page - 1) * max_depth_per_page
    bottom = min(page * max_depth_per_page, max(z_max, top + 1.0))
    return top, bottom


# ---------------------------------------------------------------------------
# tracks
# ---------------------------------------------------------------------------


def _draw_header(ax, *, project_name, borehole_id, page, depth_window, max_depth_per_page):
    ax.axis("off")
    top, bottom = depth_window
    ax.text(
        0.0, 0.78, "GEOVIEW", fontsize=14, fontweight="bold", color="#0B2545",
        transform=ax.transAxes,
    )
    ax.text(
        0.0, 0.50, "해상 시추주상도", fontsize=11, color="#1A1C1E",
        transform=ax.transAxes,
    )
    ax.text(
        0.0, 0.22, f"프로젝트: {project_name or '—'}",
        fontsize=9, color="#1A1C1E",
        transform=ax.transAxes,
    )
    ax.text(
        1.0, 0.78, f"BH-{borehole_id}", fontsize=12, fontweight="bold",
        color="#0B2545", ha="right",
        transform=ax.transAxes,
    )
    ax.text(
        1.0, 0.50, f"Page {page}  ·  {top:.1f} m – {bottom:.1f} m",
        fontsize=9, color="#1A1C1E", ha="right",
        transform=ax.transAxes,
    )
    ax.text(
        1.0, 0.22, f"페이지당 {max_depth_per_page:.0f} m",
        fontsize=8, color="#7A8089", ha="right",
        transform=ax.transAxes,
    )
    ax.axhline(0.0, color="#CBD5E0", linewidth=0.8)


def _draw_elev_track(ax, depth_window, sounding):
    top, bottom = depth_window
    ax.set_title("표고\n(m)", fontsize=8)
    ax.set_xticks([])
    ground_elev = sounding.header.ground_elev_m if sounding.header else 0.0
    ticks = np.arange(top, bottom + 1, 5.0)
    for z in ticks:
        elev = (ground_elev or 0.0) - z
        ax.text(
            0.5, z, f"{elev:+.1f}",
            ha="center", va="center", fontsize=7,
            transform=ax.get_yaxis_transform(),
        )
    format_depth_axis(ax, invert=False)


def _draw_depth_track(ax, depth_window):
    top, bottom = depth_window
    ax.set_title("심도\n(m)", fontsize=8)
    ax.set_xticks([])
    ticks = np.arange(top, bottom + 1, 1.0)
    for z in ticks:
        ax.text(
            0.5, z, f"{z:.0f}",
            ha="center", va="center", fontsize=7,
            transform=ax.get_yaxis_transform(),
        )
    ax.grid(True, axis="y", linestyle=":", linewidth=0.4, alpha=0.7)


def _draw_thickness_track(ax, depth_window, strata):
    top, bottom = depth_window
    ax.set_title("층후\n(m)", fontsize=8)
    ax.set_xticks([])
    for layer in strata:
        if layer.base_m <= top or layer.top_m >= bottom:
            continue
        ax.text(
            0.5, (layer.top_m + layer.base_m) / 2,
            f"{layer.thickness_m:.1f}",
            ha="center", va="center", fontsize=7,
        )
    ax.grid(True, axis="y", linestyle=":", linewidth=0.4, alpha=0.7)


def _draw_column_track(ax, depth_window, strata, sounding):
    top, bottom = depth_window
    ax.set_title("주상도", fontsize=8)
    ax.set_xticks([])
    ax.set_xlim(0, 1)

    if strata:
        for layer in strata:
            if layer.base_m <= top or layer.top_m >= bottom:
                continue
            color = _LEGEND_COLORS.get(layer.legend_code.upper(), "#C5CAD2")
            ax.fill_betweenx(
                [max(layer.top_m, top), min(layer.base_m, bottom)],
                0, 1, color=color, edgecolor="#7A8089", linewidth=0.6,
            )
            ax.text(
                0.5, (layer.top_m + layer.base_m) / 2, layer.legend_code,
                ha="center", va="center", fontsize=8, color="#1A1C1E",
            )
    else:
        _draw_qc_column_fallback(ax, sounding, top, bottom)


def _draw_qc_column_fallback(ax, sounding, top, bottom):
    """When strata are missing we color by normalized qc as a hint."""
    try:
        depth = depth_array(sounding)
        qc = to_mpa_array(get_raw(sounding, "qc"))
    except Exception:
        return
    window = (depth >= top) & (depth <= bottom)
    if not window.any():
        return
    d = depth[window]
    q = np.clip(qc[window], 0.01, 30.0)
    norm = (np.log10(q + 0.1) - np.log10(0.1)) / (np.log10(30.1) - np.log10(0.1))
    for i in range(len(d) - 1):
        shade = f"#{int(11 + norm[i] * 180):02x}{int(37 + norm[i] * 100):02x}{int(69 + norm[i] * 60):02x}"
        ax.fill_betweenx(
            [d[i], d[i + 1]], 0, 1, color=shade, edgecolor="none",
        )


def _draw_name_track(ax, depth_window, strata):
    top, bottom = depth_window
    ax.set_title("지층명", fontsize=8)
    ax.set_xticks([])
    ax.set_xlim(0, 1)
    for layer in strata:
        if layer.base_m <= top or layer.top_m >= bottom:
            continue
        label = layer.description or layer.geology_code or layer.legend_code
        ax.text(
            0.05, (layer.top_m + layer.base_m) / 2, label,
            ha="left", va="center", fontsize=7, color="#1A1C1E",
        )
    ax.grid(True, axis="y", linestyle=":", linewidth=0.4, alpha=0.7)


def _draw_spt_track(ax, depth_window, spt_tests):
    top, bottom = depth_window
    ax.set_title("SPT N 값", fontsize=8)
    ax.set_xlim(0, 60)
    ax.set_xlabel("N", fontsize=7)

    depths = [t.top_m for t in spt_tests if top <= t.top_m <= bottom and t.n_value is not None]
    ns = [t.n_value for t in spt_tests if top <= t.top_m <= bottom and t.n_value is not None]
    if depths:
        ax.scatter(ns, depths, color="#C0392B", s=18, zorder=4)
        ax.plot(ns, depths, color="#C0392B", linewidth=0.6, zorder=3)
    else:
        ax.text(
            0.5, (top + bottom) / 2, "no SPT",
            ha="center", va="center", fontsize=8, color="#7A8089",
            transform=ax.transAxes,
        )
    ax.grid(True, axis="both", linestyle=":", linewidth=0.4, alpha=0.6)


def _draw_footer(ax, project_name, borehole_id, page):
    ax.axis("off")
    ax.text(
        0.0, 0.5,
        f"geoview_cpt A2.7c  ·  {project_name or '—'}  ·  BH-{borehole_id}  ·  Page {page}",
        fontsize=7, color="#7A8089",
        transform=ax.transAxes,
    )
