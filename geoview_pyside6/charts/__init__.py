"""
geoview_pyside6.charts
================================
Shared chart base + formatting helpers (Phase A-1 A1.4).

All GeoView chart widgets should extend :class:`GeoViewChart` so they
inherit the 4 required interactive behaviors:

    1. pan
    2. zoom
    3. crosshair hover readout
    4. export (SVG vector + PNG raster)

Number/axis formatting lives in :mod:`formatting` — comma thousand
separators and scientific-notation suppression by default
(feedback_number_format.md — "과학표기 금지, 콤마 구분").

Public API:
    GeoViewChart, ChartAxisItem
    format_number, format_axis_label, NumberFormatError
"""
from __future__ import annotations

from geoview_pyside6.charts.formatting import (
    NumberFormatError,
    format_axis_label,
    format_number,
)

__all__ = [
    "format_number",
    "format_axis_label",
    "NumberFormatError",
    "GeoViewChart",
    "ChartAxisItem",
]


def __getattr__(name: str):
    # Lazy-import the Qt-bound classes so `from geoview_pyside6.charts import
    # format_number` works in pure-Python environments (no QApplication).
    if name in {"GeoViewChart", "ChartAxisItem"}:
        from geoview_pyside6.charts.base import ChartAxisItem, GeoViewChart

        globals()["GeoViewChart"] = GeoViewChart
        globals()["ChartAxisItem"] = ChartAxisItem
        return globals()[name]
    raise AttributeError(f"module 'geoview_pyside6.charts' has no attribute {name!r}")
