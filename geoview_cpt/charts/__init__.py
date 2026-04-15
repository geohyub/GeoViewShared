"""
geoview_cpt.charts
================================
CPT domain chart builders (Phase A-2 A2.7).

Every chart in this package is a **matplotlib-based builder** that
returns a :class:`matplotlib.figure.Figure` ready to be handed to
:class:`geoview_pyside6.export.VectorExportEngine` for the SVG+PDF+PNG
triple output.

Backend decision (Q38, Week 6):

    matplotlib for static deliverables, pyqtgraph for interactive
    viewers. A1.4 GeoViewChart (pyqtgraph) handles pan/zoom/hover in
    Phase B CPTProc — it is **not** used for Phase A-2 deliverable
    charts because its SVG exporter is broken on Qt 6.11 and
    ``gridspec``-style layouts are awkward there.

A2.7a base charts (HELMS Appendix B + Robertson 1990):

    log_plot       5-track depth profile (qc / fs / u₂ / Rf / Bq)
    sbt_chart      Robertson 1990 9-zone scatter (Fr, Qtn log-log)
    ic_profile     Ic vs depth with zone-colored bands
    su_profile     Su vs depth for multiple Nkt values
    dr_profile     Dr vs depth with Jamiolkowski density bands

A2.7b/c killers (GeoView rev7 reproduction):

    cpet_it_compat     ★ rev7 Annex 5 CPeT-IT layout (3 track + cross
                         correlation + partner branding header)
    borehole_log_kr    ★ rev7 Annex 3 Korean borehole log (30 m page
                         split + Pretendard Korean subset embed)

Pretendard font is auto-registered on first import via
:func:`geoview_pyside6.export.fonts.register_pretendard` so Korean
labels survive SVG/PDF export on any client machine.
"""
from __future__ import annotations

# Lazy imports — the Figure builders pull matplotlib only when called,
# so a pure-model consumer pays no chart tax.

__all__ = [
    "build_log_plot",
    "build_sbt_chart",
    "build_ic_profile",
    "build_su_profile",
    "build_dr_profile",
    "build_cpet_it_compat_plot",
    "build_borehole_log_kr",
]


def _register_pretendard_once() -> None:
    try:
        from geoview_pyside6.export.fonts import register_pretendard

        register_pretendard()
    except Exception:
        # Fallback: matplotlib's default sans-serif is fine for English
        pass


def __getattr__(name: str):
    if name == "build_log_plot":
        _register_pretendard_once()
        from geoview_cpt.charts.log_plot import build_log_plot

        return build_log_plot
    if name == "build_sbt_chart":
        _register_pretendard_once()
        from geoview_cpt.charts.sbt_chart import build_sbt_chart

        return build_sbt_chart
    if name == "build_ic_profile":
        _register_pretendard_once()
        from geoview_cpt.charts.ic_profile import build_ic_profile

        return build_ic_profile
    if name == "build_su_profile":
        _register_pretendard_once()
        from geoview_cpt.charts.su_profile import build_su_profile

        return build_su_profile
    if name == "build_dr_profile":
        _register_pretendard_once()
        from geoview_cpt.charts.dr_profile import build_dr_profile

        return build_dr_profile
    if name == "build_cpet_it_compat_plot":
        _register_pretendard_once()
        from geoview_cpt.charts.cpet_it_compat import build_cpet_it_compat_plot

        return build_cpet_it_compat_plot
    if name == "build_borehole_log_kr":
        _register_pretendard_once()
        from geoview_cpt.charts.borehole_log_kr import build_borehole_log_kr

        return build_borehole_log_kr
    raise AttributeError(f"module 'geoview_cpt.charts' has no attribute {name!r}")
