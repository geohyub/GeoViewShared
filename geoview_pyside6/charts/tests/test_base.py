"""Tests for geoview_pyside6.charts.base — Phase A-1 A1.4."""
from __future__ import annotations

from pathlib import Path

import pytest

from geoview_pyside6.charts import GeoViewChart


# ---------------------------------------------------------------------------
# Construction & defaults
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_default_chart(self, qapp):
        chart = GeoViewChart()
        assert chart is not None
        assert chart.crosshair_enabled is True

    def test_with_title_and_labels(self, qapp):
        chart = GeoViewChart(title="Depth", x_label="m", y_label="MPa")
        # Smoke — title accessor only needs to not crash
        assert chart.getPlotItem().titleLabel.text != ""

    def test_invert_y(self, qapp):
        chart = GeoViewChart(invert_y=True)
        assert chart.getPlotItem().getViewBox().yInverted() is True

    def test_crosshair_disabled(self, qapp):
        chart = GeoViewChart(show_crosshair=False)
        assert chart.crosshair_enabled is False


# ---------------------------------------------------------------------------
# Pan / zoom — enabled via ViewBox mouseEnabled
# ---------------------------------------------------------------------------


class TestPanZoom:
    def test_mouse_enabled_on_both_axes(self, qapp):
        chart = GeoViewChart()
        vb = chart.getPlotItem().getViewBox()
        enabled = vb.state["mouseEnabled"]
        assert enabled[0] is True  # x pan/zoom
        assert enabled[1] is True  # y pan/zoom

    def test_menu_enabled(self, qapp):
        chart = GeoViewChart()
        assert chart.getPlotItem().getViewBox().menuEnabled() is True


# ---------------------------------------------------------------------------
# Crosshair toggle
# ---------------------------------------------------------------------------


class TestCrosshair:
    def test_toggle_off_then_on(self, qapp):
        chart = GeoViewChart()
        chart.enable_crosshair(False)
        assert chart.crosshair_enabled is False
        chart.enable_crosshair(True)
        assert chart.crosshair_enabled is True

    def test_idempotent_enable(self, qapp):
        chart = GeoViewChart(show_crosshair=False)
        chart.enable_crosshair(True)
        chart.enable_crosshair(True)  # no raise
        assert chart.crosshair_enabled is True


# ---------------------------------------------------------------------------
# set_data
# ---------------------------------------------------------------------------


class TestSetData:
    def test_curve_added(self, qapp):
        chart = GeoViewChart()
        curve = chart.set_data([0, 1, 2, 3], [0, 1, 4, 9])
        assert curve is not None
        assert curve in chart.getPlotItem().items

    def test_replaces_existing_curve(self, qapp):
        chart = GeoViewChart()
        chart.set_data([0, 1], [0, 1])
        chart.set_data([0, 1, 2], [2, 4, 6])
        # Only one data item should remain after clear()
        data_items = [
            i for i in chart.getPlotItem().items if hasattr(i, "xData")
        ]
        assert len(data_items) == 1


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class TestExport:
    def _chart_with_data(self, qapp) -> GeoViewChart:
        chart = GeoViewChart(title="Exp", x_label="x", y_label="y")
        chart.set_data([0, 1, 2, 3, 4], [0, 1, 4, 9, 16])
        chart.resize(400, 300)
        return chart

    @pytest.mark.xfail(
        reason=(
            "pyqtgraph 0.14.0 SVGExporter is incompatible with PySide6 6.11 — "
            "correctCoordinates() assumes Qt emits 'x,y' path data but Qt 6.7+ "
            "uses space-separated pairs. Workaround tracked for A1.5 (Vector+Raster "
            "Export Engine), where SVG comes from a reportlab/matplotlib path."
        ),
        strict=False,
        raises=Exception,
    )
    def test_export_svg(self, qapp, tmp_path):
        chart = self._chart_with_data(qapp)
        out = chart.export_svg(tmp_path / "plot.svg")
        assert out.exists()
        body = out.read_text(encoding="utf-8", errors="ignore")
        assert "<svg" in body.lower() or body.startswith("<?xml")
        assert out.stat().st_size > 100

    def test_export_png(self, qapp, tmp_path):
        chart = self._chart_with_data(qapp)
        out = chart.export_png(tmp_path / "plot.png", scale=1.0)
        assert out.exists()
        header = out.read_bytes()[:8]
        # PNG signature
        assert header[:4] == b"\x89PNG"
        assert out.stat().st_size > 100

    def test_export_png_scale_increases_size(self, qapp, tmp_path):
        chart = self._chart_with_data(qapp)
        small = chart.export_png(tmp_path / "small.png", scale=1.0)
        big = chart.export_png(tmp_path / "big.png", scale=2.0)
        # 2x scale should be larger on disk for a meaningful plot
        assert big.stat().st_size >= small.stat().st_size

    def test_export_creates_parent(self, qapp, tmp_path):
        chart = self._chart_with_data(qapp)
        out = chart.export_png(tmp_path / "nested" / "dir" / "plot.png", scale=1.0)
        assert out.exists()

    def test_export_png_rejects_nonpositive_scale(self, qapp, tmp_path):
        chart = self._chart_with_data(qapp)
        with pytest.raises(ValueError):
            chart.export_png(tmp_path / "x.png", scale=0)


# ---------------------------------------------------------------------------
# Axis tick strings route through format_number
# ---------------------------------------------------------------------------


class TestAxisFormatting:
    def test_tick_strings_use_comma(self, qapp):
        chart = GeoViewChart()
        axis = chart.getPlotItem().getAxis("left")
        # ChartAxisItem.tickStrings is the formatter we care about
        strings = axis.tickStrings([1000.0, 2500.5], scale=1.0, spacing=500)
        assert strings == ["1,000", "2,500.50"]

    def test_tick_strings_respect_decimals(self, qapp):
        chart = GeoViewChart(decimals=0)
        axis = chart.getPlotItem().getAxis("left")
        # Python's f":.0f" uses banker's rounding → 1234.5 → 1234 (round-half-even)
        strings = axis.tickStrings([1234.6], scale=1.0, spacing=1.0)
        assert strings == ["1,235"]
