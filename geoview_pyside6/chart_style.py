"""
GeoView PySide6 — PyQtGraph Chart Style
==========================================
모든 PyQtGraph 차트에 일관된 GeoView 스타일을 적용하는 헬퍼 모듈.
"""

import pyqtgraph as pg
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QFont, QColor

from geoview_pyside6.constants import Font
from geoview_pyside6.theme_aware import c

# ── Chart Color Palettes (pyqtgraph용) ──
CHART_COLORS = [
    "#2D5F8A",  # Blue (primary)
    "#38A169",  # Green
    "#E05252",  # Red
    "#ED8936",  # Orange
    "#7C5DC7",  # Purple
    "#D97706",  # Amber
    "#0891B2",  # Teal
    "#6D5A8F",  # Muted violet
]

CHART_COLORS_BLIND = [
    "#0077BB",  # Blue
    "#33BBEE",  # Cyan
    "#009988",  # Teal
    "#EE7733",  # Orange
    "#CC3311",  # Red
    "#EE3377",  # Magenta
    "#BBBBBB",  # Gray
    "#332288",  # Indigo
]


def setup_plot(plot_widget, title="", x_label="", y_label="", grid=True):
    """PyQtGraph PlotWidget에 GeoView 표준 스타일 적용."""
    pg.setConfigOptions(antialias=True)
    plot_widget.setBackground(c().BG)

    plot_item = plot_widget.getPlotItem()

    # Grid
    if grid:
        plot_item.showGrid(x=True, y=True, alpha=0.15)

    # Axis styling
    for axis_name in ('bottom', 'left', 'top', 'right'):
        axis = plot_item.getAxis(axis_name)
        axis.setPen(pg.mkPen(c().BORDER, width=1))
        axis.setTextPen(pg.mkPen(c().DIM))
        axis.setStyle(tickFont=QFont(Font.SANS, 9))

    # Hide top/right axes
    plot_item.showAxis('top', False)
    plot_item.showAxis('right', False)

    # Disable scientific notation
    for axis_name in ('bottom', 'left'):
        plot_item.getAxis(axis_name).enableAutoSIPrefix(False)

    # Labels
    label_style = {'color': c().MUTED, 'font-size': f'{Font.XS}pt', 'font-family': Font.SANS}
    if title:
        plot_item.setTitle(title, color=c().TEXT, size=f'{Font.SM}pt')
    if x_label:
        plot_item.setLabel('bottom', x_label, **label_style)
    if y_label:
        plot_item.setLabel('left', y_label, **label_style)

    return plot_item


def add_crosshair(plot_widget, color=None, show_label=True):
    """인터랙티브 크로스헤어 + 좌표 라벨 추가.

    Returns:
        tuple: (vline, hline, label) — label은 show_label=False이면 None
    """
    c = color or "#D4A843"  # Gold default (NavQC convention)
    pen = pg.mkPen(c, width=0.8, style=Qt.PenStyle.DashLine)

    plot_item = plot_widget.getPlotItem()
    vb = plot_item.vb

    vline = pg.InfiniteLine(angle=90, movable=False, pen=pen)
    hline = pg.InfiniteLine(angle=0, movable=False, pen=pen)
    plot_item.addItem(vline, ignoreBounds=True)
    plot_item.addItem(hline, ignoreBounds=True)

    label = None
    if show_label:
        label = pg.TextItem("", color=c().TEXT, anchor=(0, 1))
        label.setFont(QFont(Font.SANS, 9))
        plot_item.addItem(label, ignoreBounds=True)

    def _on_mouse_moved(pos):
        if plot_item.sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()
            vline.setPos(x)
            hline.setPos(y)
            if label:
                label.setText(f"x={x:.4f}  y={y:.4f}")
                label.setPos(x, y)

    plot_widget.scene().sigMouseMoved.connect(_on_mouse_moved)
    return vline, hline, label


def add_stat_overlay(plot_widget, stats: dict, position="top-right"):
    """차트 코너에 통계 오버레이 텍스트 추가.

    Args:
        stats: {"Mean": "12.34", "Std": "0.56", ...}
        position: "top-right" or "top-left"
    """
    text = "\n".join(f"{k}: {v}" for k, v in stats.items())
    anchor = (1, 0) if "right" in position else (0, 0)

    item = pg.TextItem(text, color=c().MUTED, anchor=anchor)
    item.setFont(QFont(Font.SANS, 9))

    plot_item = plot_widget.getPlotItem()
    plot_item.addItem(item, ignoreBounds=True)

    # Position in view coordinates after next render
    def _update_pos():
        vr = plot_item.vb.viewRange()
        if "right" in position:
            item.setPos(vr[0][1], vr[1][1])
        else:
            item.setPos(vr[0][0], vr[1][1])

    plot_item.vb.sigRangeChanged.connect(_update_pos)
    return item


def get_pen(index: int = 0, width: float = 1.5, colorblind: bool = False):
    """팔레트에서 인덱스 기반 pen 반환."""
    palette = CHART_COLORS_BLIND if colorblind else CHART_COLORS
    color = palette[index % len(palette)]
    return pg.mkPen(color, width=width)


def get_brush(index: int = 0, alpha: int = 80, colorblind: bool = False):
    """팔레트에서 인덱스 기반 brush 반환."""
    palette = CHART_COLORS_BLIND if colorblind else CHART_COLORS
    c = QColor(palette[index % len(palette)])
    c.setAlpha(alpha)
    return pg.mkBrush(c)


def export_chart(plot_widget, path: str, width: int = 1400, height: int = 450,
                 bg_color: str = "#FFFFFF"):
    """PyQtGraph 차트를 고품질 PNG로 내보내기.

    Args:
        plot_widget: pg.PlotWidget instance
        path: 저장 경로 (.png, .svg)
        width: 출력 너비 (px)
        height: 출력 높이 (px)
        bg_color: 배경색 (인쇄용은 #FFFFFF 권장)
    """
    import pyqtgraph.exporters as exporters

    # Temporarily change background for export
    original_bg = plot_widget.backgroundBrush().color().name()
    plot_widget.setBackground(bg_color)

    if path.lower().endswith('.svg'):
        exporter = exporters.SVGExporter(plot_widget.plotItem)
    else:
        exporter = exporters.ImageExporter(plot_widget.plotItem)
        exporter.parameters()['width'] = width
        exporter.parameters()['height'] = height

    exporter.export(path)

    # Restore original background
    plot_widget.setBackground(original_bg)
