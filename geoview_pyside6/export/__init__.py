"""
geoview_pyside6.export
================================
Vector + Raster dual export engine (Phase A-1 A1.5).

Every GeoView plot that ends up in a client deliverable must ship as
three artifacts:

    - **SVG** (Illustrator/Inkscape-editable vector)
    - **PDF** (print-ready vector with embedded fonts)
    - **PNG** @2x DPI (Word-insertable raster)

This module produces all three from a single :class:`matplotlib.figure.Figure`,
registers Pretendard (OFL 1.1) as the primary font, keeps text selectable in
SVG/PDF, and writes everything via
:func:`geoview_pyside6.io_safe.atomic_writer` so a torn file never lands on
disk.

Qt/pyqtgraph widgets are **not** supported as input — the pyqtgraph SVG
exporter is broken on Qt 6.11, and the right abstraction is "build a
Figure from the underlying data". CPT log plots, SBT charts and Robertson
9-zones should all produce Figure objects that flow through this engine.

Public API:

    ExportResult, ExportError
    VectorExportEngine
    register_pretendard, pretendard_available, PRETENDARD_FAMILY
    SRGB_PALETTE, ensure_srgb_png
"""
from __future__ import annotations

from geoview_pyside6.export.color import SRGB_PALETTE, ensure_srgb_png
from geoview_pyside6.export.engine import (
    ExportError,
    ExportResult,
    VectorExportEngine,
)
from geoview_pyside6.export.fonts import (
    PRETENDARD_FAMILY,
    pretendard_available,
    register_pretendard,
)

__all__ = [
    "VectorExportEngine",
    "ExportResult",
    "ExportError",
    "register_pretendard",
    "pretendard_available",
    "PRETENDARD_FAMILY",
    "SRGB_PALETTE",
    "ensure_srgb_png",
]
