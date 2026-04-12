"""
GeoView — Application Window Icons
====================================
앱별 브랜딩 아이콘을 프로그래밍 방식으로 생성.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QPen, QLinearGradient,
    QPainterPath, QRadialGradient, QBrush,
)
from PySide6.QtCore import Qt, QSize, QRectF

from geoview_pyside6.branding import get_app_branding
from geoview_pyside6.constants import Category
from geoview_pyside6.icons.icon_engine import icon_pixmap


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

_APP_ICON_CACHE: dict[tuple[str, str, str, str, str, str], QIcon] = {}


def _mix(a: str, b: str, ratio: float) -> QColor:
    ca = QColor(a)
    cb = QColor(b)
    ratio = max(0.0, min(1.0, ratio))
    inv = 1.0 - ratio
    return QColor(
        int(ca.red() * inv + cb.red() * ratio),
        int(ca.green() * inv + cb.green() * ratio),
        int(ca.blue() * inv + cb.blue() * ratio),
    )


def _render_icon(
    size: int,
    primary: str,
    secondary: str,
    icon_name: str,
    badge_icon: str,
) -> QPixmap:
    """Create a branded multi-layer application icon."""
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = max(1, size // 14)
    radius = max(6.0, size * 0.24)
    rect = QRectF(margin, margin, size - margin * 2, size - margin * 2)

    bg_grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    bg_grad.setColorAt(0.0, _mix(primary, "#FFFFFF", 0.08))
    bg_grad.setColorAt(1.0, _mix(primary, secondary, 0.38))

    shadow_path = QPainterPath()
    shadow_path.addRoundedRect(rect.adjusted(0, 2, 0, 2), radius, radius)
    painter.fillPath(shadow_path, QColor(0, 0, 0, 38))

    card_path = QPainterPath()
    card_path.addRoundedRect(rect, radius, radius)
    painter.fillPath(card_path, QBrush(bg_grad))
    painter.setPen(QPen(_mix(primary, "#FFFFFF", 0.48), max(1, size // 32)))
    painter.drawPath(card_path)

    glow = QRadialGradient(rect.center().x(), rect.top() + rect.height() * 0.24, rect.width() * 0.62)
    glow.setColorAt(0.0, QColor(_mix(secondary, "#FFFFFF", 0.25)))
    glow.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.fillPath(card_path, glow)

    highlight = QPainterPath()
    highlight.addRoundedRect(
        QRectF(rect.left() + rect.width() * 0.10, rect.top() + rect.height() * 0.08,
               rect.width() * 0.80, rect.height() * 0.24),
        radius * 0.55,
        radius * 0.55,
    )
    painter.fillPath(highlight, QColor(255, 255, 255, 22))

    main_size = int(size * 0.44)
    main_px = icon_pixmap(icon_name, size=main_size, color="#FFFFFF")
    main_x = int(rect.center().x() - main_size / 2)
    main_y = int(rect.center().y() - main_size / 2 - size * 0.02)
    painter.drawPixmap(main_x, main_y, main_px)

    badge_size = max(12, int(size * 0.28))
    badge_rect = QRectF(
        rect.right() - badge_size * 0.98,
        rect.bottom() - badge_size * 0.94,
        badge_size,
        badge_size,
    )
    painter.setPen(QPen(QColor(255, 255, 255, 210), max(1, size // 28)))
    painter.setBrush(QColor(secondary))
    painter.drawEllipse(badge_rect)

    badge_px = icon_pixmap(badge_icon, size=int(badge_size * 0.52), color=primary)
    badge_x = int(badge_rect.center().x() - badge_px.width() / 2)
    badge_y = int(badge_rect.center().y() - badge_px.height() / 2)
    painter.drawPixmap(badge_x, badge_y, badge_px)

    painter.end()
    return pixmap


def get_app_icon(
    category: Category,
    *,
    app_name: str = "",
    primary: str | None = None,
    secondary: str | None = None,
    icon_name: str | None = None,
    badge_icon: str | None = None,
) -> QIcon:
    """앱별 멀티사이즈 아이콘 생성."""
    brand = get_app_branding(
        app_name or category.value,
        category,
        primary=primary,
        secondary=secondary,
        icon_name=icon_name or (None if app_name else _CATEGORY_ICONS.get(category, "star")),
        badge_icon=badge_icon,
    )

    cache_key = (
        app_name or category.value,
        brand.primary,
        brand.secondary,
        brand.icon_name,
        brand.badge_icon,
        category.value,
    )
    cached = _APP_ICON_CACHE.get(cache_key)
    if cached is not None:
        return cached

    qicon = QIcon()
    for size in (16, 24, 32, 48, 64, 128):
        qicon.addPixmap(
            _render_icon(
                size,
                brand.primary,
                brand.secondary,
                brand.icon_name,
                brand.badge_icon,
            )
        )
    _APP_ICON_CACHE[cache_key] = qicon
    return qicon


def set_app_icon(
    category: Category,
    *,
    app_name: str = "",
    primary: str | None = None,
    secondary: str | None = None,
    icon_name: str | None = None,
    badge_icon: str | None = None,
):
    """현재 QApplication에 앱별 아이콘 설정."""
    app = QApplication.instance()
    if app:
        app.setWindowIcon(
            get_app_icon(
                category,
                app_name=app_name,
                primary=primary,
                secondary=secondary,
                icon_name=icon_name,
                badge_icon=badge_icon,
            )
        )
