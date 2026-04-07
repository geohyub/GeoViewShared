"""
GeoView PySide6 -- TrackPlot Widget
=====================================
Interactive 2D survey route / trackline map for all QC apps.

pyqtgraph-based with:
  - Multi-line display with per-line or QC-score coloring
  - Click-to-select line (emits line_selected signal)
  - Hover tooltip showing line name, score, grade
  - Selected-line glow highlight (thicker pen + halo)
  - Crosshair cursor with coordinate display
  - Downsample for large datasets
  - Two color modes: LINE (distinct) / SCORE (green-red gradient)
  - Legend panel
  - Empty state
  - c() theme, refresh_theme(), ui_text() bilingual

Usage::

    from geoview_pyside6.widgets.track_plot import TrackPlot, LineRoute

    track = TrackPlot()
    track.set_routes([
        LineRoute("L001", "Line 001", lats=[...], lons=[...], score=92.5, status="PASS"),
        LineRoute("L002", "Line 002", lats=[...], lons=[...], score=78.0, status="WARN"),
    ])
    track.line_selected.connect(on_line_clicked)

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QStackedWidget,
)

from geoview_pyside6.constants import Font, Space, Radius, rgba
from geoview_pyside6.theme_aware import c
from geoview_pyside6.chart_style import setup_plot


# ================================================================
# Data model
# ================================================================

@dataclass
class LineRoute:
    """Route data for a single survey line.

    Attributes:
        line_id:   Unique identifier (file_id, line name, etc.)
        name:      Human-readable line name.
        lats:      Latitude array (WGS84 decimal degrees).
        lons:      Longitude array (WGS84 decimal degrees).
        score:     QC score 0-100 (used in SCORE color mode).
        grade:     Grade string ("A+", "B", etc.)  -- optional.
        status:    Status string ("PASS", "WARN", "FAIL") -- optional.
    """

    line_id: str | int = ""
    name: str = ""
    lats: list[float] = field(default_factory=list)
    lons: list[float] = field(default_factory=list)
    score: float = 0.0
    grade: str = "--"
    status: str = "N/A"

    @property
    def has_route(self) -> bool:
        return len(self.lats) >= 2 and len(self.lons) >= 2


# ================================================================
# Bilingual text
# ================================================================

_TEXTS = {
    "ko": {
        "title": "Survey Track",
        "empty": "Track data unavailable",
        "empty_detail": "QC analysis will populate the route map.",
        "mode_line": "Line",
        "mode_score": "Score",
        "lon": "Longitude",
        "lat": "Latitude",
        "lines": "Lines",
        "points": "Points",
        "score": "Score",
        "grade": "Grade",
        "hint": "Click a line to select it.",
        "legend_line": "Lines",
        "legend_score": "QC Score",

        "title_ko": "Survey Track",
        "empty_ko": "Track data unavailable",
        "empty_detail_ko": "QC analysis will populate the route map.",
    },
    "en": {
        "title": "Survey Track",
        "empty": "No track data available",
        "empty_detail": "Run QC analysis to display survey line tracks.",
        "mode_line": "Line Colors",
        "mode_score": "Score Colors",
        "lon": "Longitude",
        "lat": "Latitude",
        "lines": "Lines",
        "points": "Total Points",
        "score": "Score",
        "grade": "Grade",
        "hint": "Click a line to navigate to its analysis.",
        "legend_line": "Lines",
        "legend_score": "QC Score",
    },
}

# Override Korean with actual Korean text
_TEXTS["ko"].update({
    "title": "Track Plot",
    "empty": "Track data unavailable",
    "empty_detail": "QC analysis will populate the route map.",
    "mode_line": "Line",
    "mode_score": "Score",
    "lon": "Lon",
    "lat": "Lat",
    "lines": "Lines",
    "points": "Pts",
    "score": "Score",
    "grade": "Grade",
    "hint": "Click a line to select.",
    "legend_line": "Lines",
    "legend_score": "QC Score",
})

_current_lang = "en"


def _ui(key: str) -> str:
    return _TEXTS.get(_current_lang, _TEXTS["en"]).get(key, key)


# ================================================================
# Score -> Color mapping
# ================================================================

def _score_to_rgb(score: float) -> tuple[int, int, int]:
    """Map QC score (0-100) to green-yellow-red gradient."""
    score = max(0.0, min(100.0, score))
    if score >= 90:
        return (52, 211, 153)
    elif score >= 80:
        t = (score - 80) / 10.0
        return (
            int(52 + (251 - 52) * (1 - t)),
            int(211 + (191 - 211) * (1 - t)),
            int(153 + (36 - 153) * (1 - t)),
        )
    elif score >= 50:
        t = (score - 50) / 30.0
        return (
            int(251 + (248 - 251) * (1 - t)),
            int(191 + (113 - 191) * (1 - t)),
            int(36 + (113 - 36) * (1 - t)),
        )
    else:
        return (248, 113, 113)


def _score_color(score: float) -> QColor:
    r, g, b = _score_to_rgb(score)
    return QColor(r, g, b)


# Line color palette (distinct per-line)
_LINE_PALETTE = [
    "#3b82f6", "#34d399", "#f87171", "#fbbf24",
    "#a78bfa", "#14b8a6", "#fb7185", "#6366f1",
    "#f59e0b", "#0ea5e9", "#8b5cf6", "#10b981",
    "#ef4444", "#06b6d4", "#d946ef", "#84cc16",
]


def _line_color(index: int) -> QColor:
    return QColor(_LINE_PALETTE[index % len(_LINE_PALETTE)])


# ================================================================
# Hover tooltip
# ================================================================

class _HoverLabel(QLabel):
    """Floating tooltip label that appears near the cursor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("trackPlotHover")
        self.setWordWrap(True)
        self.setFixedWidth(210)
        self.hide()
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(
            f"QLabel#trackPlotHover {{"
            f"  background: {c().NAVY}; color: {c().TEXT};"
            f"  border: 1px solid {c().BORDER};"
            f"  border-radius: {Radius.SM}px;"
            f"  padding: {Space.XS}px {Space.SM}px;"
            f"  font-size: {Font.XS}px;"
            f"}}"
        )

    def show_at(self, pos: QPointF, text: str):
        self.setText(text)
        self.adjustSize()
        gp = pos.toPoint()
        self.move(gp.x() + 14, gp.y() - self.height() - 10)
        self.show()
        self.raise_()

    def refresh_theme(self):
        self._apply_style()


# ================================================================
# Empty state
# ================================================================

class _EmptyState(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon = QLabel("~")
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title = QLabel(_ui("empty"))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._detail = QLabel(_ui("empty_detail"))
        self._detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail.setWordWrap(True)
        self._detail.setMaximumWidth(340)

        layout.addStretch()
        layout.addWidget(self._icon)
        layout.addWidget(self._title)
        layout.addWidget(self._detail)
        layout.addStretch()
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"background: {c().BG};")
        self._icon.setStyleSheet(
            f"font-size: 36px; color: {c().DIM}; background: transparent;")
        self._title.setStyleSheet(
            f"font-size: {Font.MD}px; font-weight: {Font.SEMIBOLD};"
            f" color: {c().TEXT}; background: transparent;")
        self._detail.setStyleSheet(
            f"font-size: {Font.XS}px; color: {c().MUTED};"
            f" background: transparent; margin-top: {Space.XS}px;")

    def refresh_theme(self):
        self._apply_style()

    def retranslate(self):
        self._title.setText(_ui("empty"))
        self._detail.setText(_ui("empty_detail"))


# ================================================================
# Legend panel
# ================================================================

class _LegendPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("trackLegend")
        self.setFixedWidth(170)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(Space.SM, Space.SM, Space.SM, Space.SM)
        self._layout.setSpacing(2)
        self._items: list[QWidget] = []
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(
            f"QFrame#trackLegend {{"
            f"  background: {c().DARK};"
            f"  border: 1px solid {c().BORDER};"
            f"  border-radius: {Radius.SM}px;"
            f"}}"
        )

    def clear(self):
        for w in self._items:
            self._layout.removeWidget(w)
            w.deleteLater()
        self._items.clear()

    def add_header(self, text: str):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size: {Font.XS}px; font-weight: {Font.SEMIBOLD};"
            f" color: {c().MUTED}; background: transparent; padding-bottom: 2px;")
        self._layout.addWidget(lbl)
        self._items.append(lbl)

    def add_entry(self, color: QColor, label: str, detail: str = ""):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 1, 0, 1)
        rl.setSpacing(Space.XS)

        swatch = QFrame()
        swatch.setFixedSize(10, 10)
        swatch.setStyleSheet(
            f"background: {color.name()}; border-radius: 2px; border: none;")
        rl.addWidget(swatch)

        name_lbl = QLabel(label)
        name_lbl.setStyleSheet(
            f"font-size: {Font.XS}px; color: {c().TEXT}; background: transparent;")
        rl.addWidget(name_lbl, 1)

        if detail:
            det_lbl = QLabel(detail)
            det_lbl.setStyleSheet(
                f"font-size: {Font.XS}px; color: {c().DIM}; background: transparent;")
            rl.addWidget(det_lbl)

        self._layout.addWidget(row)
        self._items.append(row)

    def finalize(self):
        self._layout.addStretch()

    def refresh_theme(self):
        self._apply_style()


# ================================================================
# TrackPlot (main widget)
# ================================================================

class TrackPlot(QWidget):
    """Interactive 2D survey track plot for QC apps.

    Signals:
        line_selected(line_id): emitted when user clicks a line on the map.
            ``line_id`` matches ``LineRoute.line_id``.
    """

    line_selected = Signal(object)  # line_id can be str or int
    lines_selected = Signal(list)   # list of line_ids (multi-select)

    COLOR_MODE_LINE = "line"
    COLOR_MODE_SCORE = "score"

    MAX_POINTS_PER_LINE = 3000

    def __init__(self, parent=None, *, show_legend: bool = True,
                 show_toolbar: bool = True, show_hint: bool = True,
                 multi_select: bool = False):
        super().__init__(parent)
        self._routes: list[LineRoute] = []
        self._color_mode = self.COLOR_MODE_LINE
        self._plot_items: list[tuple[pg.PlotDataItem, LineRoute]] = []
        self._scatter_items: list[tuple[pg.ScatterPlotItem, LineRoute]] = []
        self._highlight_items: list[pg.PlotDataItem] = []
        self._hovered_route: Optional[LineRoute] = None
        self._selected_id: Optional[str | int] = None
        self._selected_ids: set = set()  # multi-select set
        self._multi_select = multi_select
        self._auto_range_on_select = False  # never zoom on click

        self._show_legend = show_legend
        self._show_toolbar = show_toolbar
        self._show_hint = show_hint

        self._build_ui()
        self._apply_styles()

    # ----------------------------------------------------------------
    # Build UI
    # ----------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar
        if self._show_toolbar:
            toolbar = QFrame()
            toolbar.setObjectName("trackToolbar")
            tb = QHBoxLayout(toolbar)
            tb.setContentsMargins(Space.MD, Space.SM, Space.MD, Space.SM)
            tb.setSpacing(Space.SM)

            self._title_label = QLabel(_ui("title"))
            self._title_label.setObjectName("trackTitle")
            tb.addWidget(self._title_label)

            tb.addStretch()

            self._stats_label = QLabel("")
            self._stats_label.setObjectName("trackStats")
            tb.addWidget(self._stats_label)

            self._btn_line = QPushButton(_ui("mode_line"))
            self._btn_line.setObjectName("trackBtn")
            self._btn_line.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_line.setCheckable(True)
            self._btn_line.setChecked(True)
            self._btn_line.clicked.connect(
                lambda: self._set_color_mode(self.COLOR_MODE_LINE))
            tb.addWidget(self._btn_line)

            self._btn_score = QPushButton(_ui("mode_score"))
            self._btn_score.setObjectName("trackBtn")
            self._btn_score.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_score.setCheckable(True)
            self._btn_score.clicked.connect(
                lambda: self._set_color_mode(self.COLOR_MODE_SCORE))
            tb.addWidget(self._btn_score)

            root.addWidget(toolbar)
        else:
            self._title_label = None
            self._stats_label = None
            self._btn_line = None
            self._btn_score = None

        # Content stack: empty / map
        self._stack = QStackedWidget()

        self._empty = _EmptyState()
        self._stack.addWidget(self._empty)

        self._map_container = QWidget()
        map_layout = QHBoxLayout(self._map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)
        map_layout.setSpacing(0)

        # pyqtgraph plot
        pg.setConfigOptions(antialias=True)
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(c().BG)
        self._plot_widget.getPlotItem().setAspectLocked(True)
        self._plot_widget.setMouseTracking(True)
        self._setup_plot()
        map_layout.addWidget(self._plot_widget, 1)

        # Legend
        self._legend = _LegendPanel()
        if self._show_legend:
            map_layout.addWidget(self._legend)

        self._stack.addWidget(self._map_container)
        root.addWidget(self._stack, 1)

        # Hover tooltip (parented to self for overlay)
        self._hover_label = _HoverLabel(self)

        # Hint bar
        if self._show_hint:
            self._hint_label = QLabel(_ui("hint"))
            self._hint_label.setObjectName("trackHint")
            root.addWidget(self._hint_label)
        else:
            self._hint_label = None

    def _setup_plot(self):
        plot_item = setup_plot(
            self._plot_widget,
            title="",
            x_label=_ui("lon"),
            y_label=_ui("lat"),
            grid=True,
        )
        self._plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self._plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)

        # Crosshair
        pen = pg.mkPen(c().CROSSHAIR if hasattr(c(), "CROSSHAIR") else c().BORDER_H,
                       width=0.6, style=Qt.PenStyle.DashLine)
        self._vline = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self._hline = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        plot_item.addItem(self._vline, ignoreBounds=True)
        plot_item.addItem(self._hline, ignoreBounds=True)

    # ----------------------------------------------------------------
    # Style
    # ----------------------------------------------------------------

    def _apply_styles(self):
        self.setStyleSheet(f"background: {c().BG};")

        if self._show_toolbar:
            toolbar_css = (
                f"QFrame#trackToolbar {{"
                f"  background: {c().BG_ALT};"
                f"  border-bottom: 1px solid {c().BORDER};"
                f"}}"
            )
            for child in self.findChildren(QFrame):
                if child.objectName() == "trackToolbar":
                    child.setStyleSheet(toolbar_css)

            if self._title_label:
                self._title_label.setStyleSheet(
                    f"font-size: {Font.SM}px; font-weight: {Font.SEMIBOLD};"
                    f" color: {c().TEXT_BRIGHT}; background: transparent;")

            if self._stats_label:
                self._stats_label.setStyleSheet(
                    f"font-size: {Font.XS}px; color: {c().MUTED};"
                    f" background: transparent;")

            btn_css = (
                f"QPushButton#trackBtn {{"
                f"  background: {c().DARK}; color: {c().MUTED};"
                f"  border: 1px solid {c().BORDER}; border-radius: {Radius.SM}px;"
                f"  padding: 4px 12px; font-size: {Font.XS}px;"
                f"}}"
                f"QPushButton#trackBtn:checked {{"
                f"  background: {c().CYAN}; color: {c().BG};"
                f"  border-color: {c().CYAN}; font-weight: {Font.SEMIBOLD};"
                f"}}"
                f"QPushButton#trackBtn:hover {{ background: {c().SLATE}; }}"
                f"QPushButton#trackBtn:checked:hover {{ background: {c().CYAN_H}; }}"
            )
            if self._btn_line:
                self._btn_line.setStyleSheet(btn_css)
            if self._btn_score:
                self._btn_score.setStyleSheet(btn_css)

        if self._hint_label:
            self._hint_label.setStyleSheet(
                f"QLabel#trackHint {{"
                f"  font-size: {Font.XS}px; color: {c().DIM};"
                f"  padding: {Space.XS}px {Space.MD}px;"
                f"  background: {c().BG_ALT};"
                f"  border-top: 1px solid {c().BORDER};"
                f"}}")

        self._plot_widget.setBackground(c().BG)
        plot_item = self._plot_widget.getPlotItem()
        for axis_name in ("bottom", "left"):
            axis = plot_item.getAxis(axis_name)
            axis.setPen(pg.mkPen(c().BORDER, width=1))
            axis.setTextPen(pg.mkPen(c().DIM))

    def refresh_theme(self):
        """Reapply theme colors after theme switch."""
        self._apply_styles()
        self._empty.refresh_theme()
        self._legend.refresh_theme()
        self._hover_label.refresh_theme()
        if self._routes:
            self._render_routes(fit_view=False)

    def retranslate_ui(self):
        """Update bilingual labels."""
        if self._title_label:
            self._title_label.setText(_ui("title"))
        if self._btn_line:
            self._btn_line.setText(_ui("mode_line"))
        if self._btn_score:
            self._btn_score.setText(_ui("mode_score"))
        if self._hint_label:
            self._hint_label.setText(_ui("hint"))
        self._empty.retranslate()

        plot_item = self._plot_widget.getPlotItem()
        label_style = {"color": c().MUTED, "font-size": f"{Font.XS}pt"}
        plot_item.setLabel("bottom", _ui("lon"), **label_style)
        plot_item.setLabel("left", _ui("lat"), **label_style)

        if self._routes:
            self._update_stats()
            self._rebuild_legend()

    @staticmethod
    def set_language(lang: str):
        """Set widget language globally ("ko" or "en")."""
        global _current_lang
        _current_lang = lang if lang in _TEXTS else "en"

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def set_routes(self, routes: list[LineRoute]):
        """Load line routes into the track plot.

        Args:
            routes: List of LineRoute objects. Each must have
                    at least 2 lat/lon points to be plotted.
        """
        self._routes = list(routes)
        self._selected_ids.clear()
        self._selected_id = None
        valid = [r for r in self._routes if r.has_route]

        if not valid:
            self._stack.setCurrentIndex(0)
            if self._stats_label:
                self._stats_label.setText("")
            return

        self._stack.setCurrentIndex(1)
        self._update_stats()
        self._render_routes(fit_view=True)  # auto-range on initial load
        self._rebuild_legend()

    def clear(self):
        """Remove all routes and reset to empty state."""
        self._routes.clear()
        self._clear_plot_items()
        self._stack.setCurrentIndex(0)
        if self._stats_label:
            self._stats_label.setText("")
        self._legend.clear()

    def select_line(self, line_id):
        """Programmatically select a line by its line_id.
        Does NOT change zoom/pan -- just highlights the line.
        """
        self._selected_id = line_id
        if self._multi_select:
            self._selected_ids = {line_id} if line_id is not None else set()
        self._apply_selection_highlight()

    def select_lines(self, line_ids: list):
        """Programmatically select multiple lines (multi-select mode)."""
        self._selected_ids = set(line_ids)
        self._selected_id = line_ids[0] if line_ids else None
        self._apply_selection_highlight()

    def get_selected_ids(self) -> list:
        """Return list of currently selected line IDs."""
        if self._multi_select:
            return list(self._selected_ids)
        return [self._selected_id] if self._selected_id is not None else []

    def set_color_mode(self, mode: str):
        """Set color mode externally: 'line' or 'score'."""
        self._set_color_mode(mode)

    @property
    def routes(self) -> list[LineRoute]:
        return list(self._routes)

    # ----------------------------------------------------------------
    # Stats
    # ----------------------------------------------------------------

    def _update_stats(self):
        if not self._stats_label:
            return
        valid = [r for r in self._routes if r.has_route]
        total_pts = sum(len(r.lats) for r in valid)
        self._stats_label.setText(
            f"{_ui('lines')}: {len(valid)}  |  "
            f"{_ui('points')}: {total_pts:,}")

    # ----------------------------------------------------------------
    # Rendering
    # ----------------------------------------------------------------

    def _clear_plot_items(self):
        plot_item = self._plot_widget.getPlotItem()
        for item, _ in self._plot_items:
            plot_item.removeItem(item)
        for item, _ in self._scatter_items:
            plot_item.removeItem(item)
        for item in self._highlight_items:
            plot_item.removeItem(item)
        self._plot_items.clear()
        self._scatter_items.clear()
        self._highlight_items.clear()

    def _render_routes(self, *, fit_view: bool = False):
        """Render all routes. If fit_view=True, auto-range to fit all data.
        Otherwise preserve the current zoom/pan state.
        """
        self._clear_plot_items()
        plot_item = self._plot_widget.getPlotItem()
        valid = [r for r in self._routes if r.has_route]
        if not valid:
            return

        # Build the set of selected IDs for multi-select
        sel_ids = self._selected_ids if self._multi_select else set()
        single_sel = self._selected_id

        for idx, route in enumerate(valid):
            lats = np.array(route.lats, dtype=np.float64)
            lons = np.array(route.lons, dtype=np.float64)

            # Downsample
            if len(lats) > self.MAX_POINTS_PER_LINE:
                step = max(1, len(lats) // self.MAX_POINTS_PER_LINE)
                lats = lats[::step]
                lons = lons[::step]

            color = self._get_color(idx, route)
            is_selected = (route.line_id == single_sel or
                           route.line_id in sel_ids)

            # Line
            pen_width = 3.5 if is_selected else 2.0
            pen = pg.mkPen(color, width=pen_width)
            line_item = plot_item.plot(lons, lats, pen=pen, name=route.name)
            self._plot_items.append((line_item, route))

            # Glow halo for selected line
            if is_selected:
                glow_color = QColor(color)
                glow_color.setAlpha(60)
                glow_pen = pg.mkPen(glow_color, width=8)
                glow_item = plot_item.plot(lons, lats, pen=glow_pen)
                self._highlight_items.append(glow_item)

            # Start marker (circle)
            start_scatter = pg.ScatterPlotItem(
                [lons[0]], [lats[0]], size=10,
                pen=pg.mkPen(c().TEXT_BRIGHT, width=1.5),
                brush=pg.mkBrush(color), symbol="o")
            plot_item.addItem(start_scatter)
            self._scatter_items.append((start_scatter, route))

            # End marker (square)
            end_scatter = pg.ScatterPlotItem(
                [lons[-1]], [lats[-1]], size=10,
                pen=pg.mkPen(c().TEXT_BRIGHT, width=1.5),
                brush=pg.mkBrush(color), symbol="s")
            plot_item.addItem(end_scatter)
            self._scatter_items.append((end_scatter, route))

        if fit_view:
            self._plot_widget.autoRange()

    def _get_color(self, index: int, route: LineRoute) -> QColor:
        # Unanalyzed files (grade="--") always show as muted grey
        if route.grade == "--":
            return QColor(c().MUTED)
        if self._color_mode == self.COLOR_MODE_SCORE:
            return _score_color(route.score)
        return _line_color(index)

    def _set_color_mode(self, mode: str):
        self._color_mode = mode
        if self._btn_line:
            self._btn_line.setChecked(mode == self.COLOR_MODE_LINE)
        if self._btn_score:
            self._btn_score.setChecked(mode == self.COLOR_MODE_SCORE)
        if self._routes:
            self._render_routes(fit_view=False)
            self._rebuild_legend()

    def _apply_selection_highlight(self):
        """Re-render with selection highlight applied (no zoom change)."""
        if self._routes:
            self._render_routes(fit_view=False)

    # ----------------------------------------------------------------
    # Legend
    # ----------------------------------------------------------------

    def _rebuild_legend(self):
        self._legend.clear()
        valid = [r for r in self._routes if r.has_route]
        if not valid:
            return

        if self._color_mode == self.COLOR_MODE_LINE:
            self._legend.add_header(_ui("legend_line"))
            for idx, route in enumerate(valid):
                if route.grade == "--":
                    color = QColor(c().MUTED)
                    detail = "--"
                else:
                    color = _line_color(idx)
                    detail = f"{route.grade} ({route.score:.0f})" if route.score else ""
                self._legend.add_entry(color, route.name, detail)
        else:
            self._legend.add_header(_ui("legend_score"))
            for idx, route in enumerate(valid):
                if route.grade == "--":
                    color = QColor(c().MUTED)
                    detail = "--"
                else:
                    color = _score_color(route.score)
                    detail = f"{route.score:.0f}"
                self._legend.add_entry(color, route.name, detail)

        self._legend.finalize()

    # ----------------------------------------------------------------
    # Interaction
    # ----------------------------------------------------------------

    def _on_mouse_moved(self, pos):
        vb = self._plot_widget.getPlotItem().vb
        if not self._plot_widget.sceneBoundingRect().contains(pos):
            self._hover_label.hide()
            return

        mouse_pt = vb.mapSceneToView(pos)
        mx, my = mouse_pt.x(), mouse_pt.y()
        self._vline.setPos(mx)
        self._hline.setPos(my)

        # Find nearest route
        best_route: Optional[LineRoute] = None
        best_dist = float("inf")

        for _, route in self._plot_items:
            if not route.has_route:
                continue
            lats = np.array(route.lats, dtype=np.float64)
            lons = np.array(route.lons, dtype=np.float64)
            if len(lats) > 500:
                step = max(1, len(lats) // 500)
                lats = lats[::step]
                lons = lons[::step]

            dists = (lons - mx) ** 2 + (lats - my) ** 2
            min_d = float(np.min(dists))
            if min_d < best_dist:
                best_dist = min_d
                best_route = route

        # Threshold: only show if reasonably close
        view_range = vb.viewRange()
        x_range = view_range[0][1] - view_range[0][0]
        threshold = (x_range * 0.03) ** 2

        if best_route and best_dist < threshold:
            self._hovered_route = best_route
            tooltip = (
                f"<b>{best_route.name}</b><br>"
                f"{_ui('score')}: {best_route.score:.1f}  "
                f"{_ui('grade')}: {best_route.grade}<br>"
                f"{_ui('points')}: {len(best_route.lats):,}"
            )
            global_pos = self._plot_widget.mapToParent(
                self._plot_widget.mapFromScene(pos))
            self._hover_label.show_at(
                QPointF(float(global_pos.x()), float(global_pos.y())),
                tooltip)
        else:
            self._hovered_route = None
            self._hover_label.hide()

    def _on_mouse_clicked(self, event):
        if not self._hovered_route:
            return

        line_id = self._hovered_route.line_id
        modifiers = event.modifiers() if hasattr(event, 'modifiers') else Qt.KeyboardModifier.NoModifier

        if self._multi_select and modifiers & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+click: toggle selection
            if line_id in self._selected_ids:
                self._selected_ids.discard(line_id)
            else:
                self._selected_ids.add(line_id)
            self._selected_id = line_id if self._selected_ids else None
            self._render_routes(fit_view=False)  # preserve zoom
            self.lines_selected.emit(list(self._selected_ids))
        else:
            # Normal click: single select, preserve zoom
            self._selected_id = line_id
            if self._multi_select:
                self._selected_ids = {line_id}
            self._render_routes(fit_view=False)  # preserve zoom
            self.line_selected.emit(line_id)
            if self._multi_select:
                self.lines_selected.emit([line_id])
