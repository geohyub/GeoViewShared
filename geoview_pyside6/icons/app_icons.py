"""
GeoView — Application Window Icons
====================================
카테고리별 앱 아이콘을 프로그래밍 방식으로 생성.
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen
from PySide6.QtCore import Qt, QSize, QRect

from geoview_pyside6.constants import Category, CATEGORY_THEMES, Dark, Font


# Category → Lucide icon name mapping
_CATEGORY_ICONS = {
    Category.QC: "check-circle",
    Category.PROCESSING: "settings",
    Category.PREPROCESSING: "shuffle",
    Category.MANAGEMENT: "layout-dashboard",
    Category.VALIDATION: "search",
    Category.UTILITIES: "star",
    Category.AI: "activity",
}


def _render_icon(size: int, accent: str, icon_name: str) -> QPixmap:
    """Create a single-size app icon: colored circle + white Lucide icon."""
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Circle background with accent color
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(accent))
    margin = max(1, size // 16)
    painter.drawEllipse(margin, margin, size - margin * 2, size - margin * 2)

    # Center Lucide icon (white)
    try:
        from geoview_pyside6.icons.icon_engine import _load_svg, SvgIconEngine
        svg = _load_svg(icon_name)
        if svg:
            engine = SvgIconEngine(svg, "#FFFFFF")
            icon_size = int(size * 0.55)
            offset = (size - icon_size) // 2
            engine.paint(painter, QRect(offset, offset, icon_size, icon_size),
                        QIcon.Mode.Normal, QIcon.State.Off)
    except Exception:
        # Fallback: draw "G" letter
        painter.setPen(QColor("#FFFFFF"))
        f = QFont(Font.SANS, int(size * 0.4))
        f.setWeight(QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "G")

    painter.end()
    return pixmap


def get_app_icon(category: Category) -> QIcon:
    """카테고리별 멀티사이즈 앱 아이콘 생성."""
    theme = CATEGORY_THEMES.get(category, CATEGORY_THEMES[Category.PROCESSING])
    icon_name = _CATEGORY_ICONS.get(category, "star")

    qicon = QIcon()
    for size in (16, 24, 32, 48, 64, 128):
        qicon.addPixmap(_render_icon(size, theme.accent, icon_name))
    return qicon


def set_app_icon(category: Category):
    """현재 QApplication에 카테고리별 아이콘 설정."""
    app = QApplication.instance()
    if app:
        app.setWindowIcon(get_app_icon(category))
