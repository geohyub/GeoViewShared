"""
geoview_pyside6.charts.base
================================
GeoViewChart — shared interactive chart base (Phase A-1 A1.4).

Every GeoView chart widget extends :class:`GeoViewChart` so it inherits
the four required interactive behaviors (master plan §5.1 A1.4):

    1. **Pan**     — left-drag on the view box.
    2. **Zoom**    — mouse wheel.
    3. **Crosshair hover** — two :class:`pg.InfiniteLine` + a floating
       text item showing formatted (x, y) via
       :func:`geoview_pyside6.charts.formatting.format_number`.
    4. **Export**  — :meth:`export_svg` + :meth:`export_png`.

The class is a thin, conservative subclass of ``pyqtgraph.PlotWidget`` —
no branding, no theme coupling — so individual apps can style on top
without fighting the base. The CPT log plot, SBT chart, Robertson
9-zone and MagQC track plot all layer styling and domain logic on top.

The class imports Qt lazily inside __init__ so that module import in
pure-Python contexts (formatting tests, documentation generation) does
not spin up a GUI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor

from geoview_pyside6.charts.formatting import format_number

__all__ = ["ChartAxisItem", "GeoViewChart"]


# ---------------------------------------------------------------------------
# Axis tick formatting
# ---------------------------------------------------------------------------


class ChartAxisItem(pg.AxisItem):
    """AxisItem that renders tick strings via ``format_number``."""

    def __init__(self, *args: Any, decimals: int = 2, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._decimals = decimals

    def set_decimals(self, decimals: int) -> None:
        self._decimals = decimals
        self.picture = None
        self.update()

    def tickStrings(self, values: Iterable[float], scale: float, spacing: float):  # noqa: N802 — pg API
        return [format_number(float(v) * scale, decimals=self._decimals) for v in values]


# ---------------------------------------------------------------------------
# GeoViewChart
# ---------------------------------------------------------------------------


class GeoViewChart(pg.PlotWidget):
    """
    Shared base for every GeoView chart widget.

    Args:
        title:          optional plot title.
        x_label:        x-axis label.
        y_label:        y-axis label.
        decimals:       number of decimals rendered on axes and crosshair.
        show_crosshair: enable the hover crosshair readout (default True).
        invert_y:       if True, y grows downward (used by depth-axis charts).
        background:     pyqtgraph background. Defaults to ``"w"`` (white) —
                        exports render cleanly on white paper.
    """

    def __init__(
        self,
        *,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        decimals: int = 2,
        show_crosshair: bool = True,
        invert_y: bool = False,
        background: str | QColor = "w",
        parent=None,
    ) -> None:
        axis_items = {
            "left": ChartAxisItem(orientation="left", decimals=decimals),
            "bottom": ChartAxisItem(orientation="bottom", decimals=decimals),
        }
        super().__init__(parent=parent, background=background, axisItems=axis_items)

        self._decimals = decimals
        if title:
            self.setTitle(title)
        if x_label:
            self.setLabel("bottom", x_label)
        if y_label:
            self.setLabel("left", y_label)

        plot_item = self.getPlotItem()
        plot_item.showGrid(x=True, y=True, alpha=0.25)
        plot_item.getViewBox().setMouseEnabled(x=True, y=True)
        plot_item.getViewBox().setMenuEnabled(True)
        if invert_y:
            plot_item.invertY(True)

        # Crosshair
        self._crosshair_enabled = False
        self._v_line: pg.InfiniteLine | None = None
        self._h_line: pg.InfiniteLine | None = None
        self._readout: pg.TextItem | None = None
        self._proxy: pg.SignalProxy | None = None
        if show_crosshair:
            self.enable_crosshair(True)

    # ------------------------------------------------------------------
    # Crosshair
    # ------------------------------------------------------------------

    def enable_crosshair(self, enabled: bool) -> None:
        """Toggle the hover crosshair readout."""
        if enabled and not self._crosshair_enabled:
            pen = pg.mkPen(color=(120, 120, 120), width=1, style=Qt.DashLine)
            self._v_line = pg.InfiniteLine(angle=90, movable=False, pen=pen)
            self._h_line = pg.InfiniteLine(angle=0, movable=False, pen=pen)
            self._readout = pg.TextItem(
                "", anchor=(0, 1), color=(30, 30, 30), fill=(255, 255, 255, 200)
            )
            plot_item = self.getPlotItem()
            plot_item.addItem(self._v_line, ignoreBounds=True)
            plot_item.addItem(self._h_line, ignoreBounds=True)
            plot_item.addItem(self._readout, ignoreBounds=True)
            self._proxy = pg.SignalProxy(
                plot_item.scene().sigMouseMoved,
                rateLimit=60,
                slot=self._on_mouse_moved,
            )
            self._crosshair_enabled = True
        elif not enabled and self._crosshair_enabled:
            plot_item = self.getPlotItem()
            for item in (self._v_line, self._h_line, self._readout):
                if item is not None:
                    plot_item.removeItem(item)
            self._v_line = None
            self._h_line = None
            self._readout = None
            self._proxy = None
            self._crosshair_enabled = False

    @property
    def crosshair_enabled(self) -> bool:
        return self._crosshair_enabled

    def _on_mouse_moved(self, evt: tuple) -> None:
        if not self._crosshair_enabled or self._v_line is None:
            return
        pos = evt[0]
        plot_item = self.getPlotItem()
        vb = plot_item.getViewBox()
        if not plot_item.sceneBoundingRect().contains(pos):
            return
        mouse_point: QPointF = vb.mapSceneToView(pos)
        x = mouse_point.x()
        y = mouse_point.y()
        self._v_line.setPos(x)
        self._h_line.setPos(y)
        assert self._readout is not None
        self._readout.setPos(x, y)
        self._readout.setText(
            f"x = {format_number(x, decimals=self._decimals)}\n"
            f"y = {format_number(y, decimals=self._decimals)}"
        )

    # ------------------------------------------------------------------
    # Data convenience
    # ------------------------------------------------------------------

    def set_data(
        self,
        x: Iterable[float],
        y: Iterable[float],
        *,
        pen: Any = None,
        symbol: str | None = None,
        name: str | None = None,
    ) -> pg.PlotDataItem:
        """Replace the chart's content with a single curve. Returns the curve item."""
        self.getPlotItem().clear()
        return self.getPlotItem().plot(
            list(x),
            list(y),
            pen=pen or pg.mkPen(color=(20, 100, 200), width=2),
            symbol=symbol,
            name=name,
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_svg(self, path: str | Path) -> Path:
        """
        Export the plot as SVG (vector). Returns the resolved path.

        NOTE: pyqtgraph 0.14.0 + PySide6 6.11 ship a known SVGExporter
        incompatibility (correctCoordinates assumes Qt emits 'x,y' path
        data but Qt 6.7+ uses space-separated pairs). A1.5 replaces this
        call path with a reportlab/matplotlib-based vector engine; until
        then callers should prefer :meth:`export_png` and treat SVG as
        best-effort. The test suite marks the SVG export case xfail.
        """
        from pyqtgraph.exporters import SVGExporter

        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        exporter = SVGExporter(self.getPlotItem())
        exporter.export(str(out))
        return out

    def export_png(self, path: str | Path, *, scale: float = 2.0) -> Path:
        """
        Export the plot as PNG (raster) at ``scale`` × base resolution.

        ``scale=2.0`` (default) matches the PDF report pipeline's @2x target.
        """
        from pyqtgraph.exporters import ImageExporter

        if scale <= 0:
            raise ValueError("scale must be positive")
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        exporter = ImageExporter(self.getPlotItem())
        try:
            base_w = int(exporter.parameters()["width"])
            exporter.parameters()["width"] = max(1, int(base_w * scale))
        except Exception:
            pass
        exporter.export(str(out))
        return out
