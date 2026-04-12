"""
GeoView splash screen with app-specific branding.

The static background is prerendered once per splash instance so progress updates
only repaint the dynamic footer, which keeps startup animation smooth.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtCore import Qt, QRect, QRectF, QTimer, QPointF

from geoview_pyside6.branding import get_app_branding
from geoview_pyside6.constants import Category, Font
from geoview_pyside6.icons.icon_engine import icon_pixmap


_BG_TOP = "#0B0E12"
_BG_BOT = "#11161D"
_TEXT_BRIGHT = "#F5F7FA"
_TEXT_MUTED = "#9CA5B3"
_TEXT_DIM = "#6C7786"
_BORDER = "#202734"
_TRACK_BG = "#1D2430"

W, H = 560, 336
_TRACK_Y = H - 34
_TRACK_MARGIN = 42
_TRACK_W = W - _TRACK_MARGIN * 2


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


class GeoViewSplash(QSplashScreen):
    """App-branded splash with cached background and animated progress."""

    def __init__(self, app_name: str, version: str = "", category: Category = Category.PROCESSING):
        self._app_name = app_name
        self._version = version
        self._category = category
        self._brand = get_app_branding(app_name, category)
        self._progress = 0.0
        self._status_text = "Loading..."
        self._static_base = self._render_static_base()

        super().__init__(self._render_pixmap())
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(40)
        self._auto_timer.timeout.connect(self._auto_advance)
        self._auto_timer.start()

    def _auto_advance(self):
        if self._progress < 0.88:
            remaining = 0.88 - self._progress
            self._progress += remaining * 0.075
            self._update_pixmap()

    def set_status(self, message: str):
        if message == self._status_text and self._progress >= 1.0:
            return
        self._status_text = message
        if message.lower() in ("ready", "done", "완료"):
            self._progress = 1.0
            self._auto_timer.stop()
        self._update_pixmap()
        QApplication.processEvents()

    def set_progress(self, value: float):
        self._progress = max(0.0, min(1.0, value))
        self._update_pixmap()

    def finish_with_delay(self, window, delay_ms: int = 420):
        self._progress = 1.0
        self._auto_timer.stop()
        self._update_pixmap()
        QTimer.singleShot(delay_ms, lambda: self.finish(window))

    def _update_pixmap(self):
        self.setPixmap(self._render_pixmap())
        self.repaint()

    def _render_static_base(self) -> QPixmap:
        primary = self._brand.primary
        secondary = self._brand.secondary
        pr = QColor(primary)
        sr = QColor(secondary)

        pixmap = QPixmap(W, H)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        root = QPainterPath()
        root.addRoundedRect(QRectF(0.5, 0.5, W - 1, H - 1), 16, 16)

        bg_grad = QLinearGradient(0, 0, 0, H)
        bg_grad.setColorAt(0.0, QColor(_BG_TOP))
        bg_grad.setColorAt(1.0, QColor(_BG_BOT))
        painter.fillPath(root, bg_grad)

        top_glow = QRadialGradient(QPointF(W * 0.52, 18), 260)
        top_glow.setColorAt(0.0, QColor(pr.red(), pr.green(), pr.blue(), 46))
        top_glow.setColorAt(0.5, QColor(pr.red(), pr.green(), pr.blue(), 12))
        top_glow.setColorAt(1.0, QColor(pr.red(), pr.green(), pr.blue(), 0))
        painter.fillRect(0, 0, W, 180, top_glow)

        side_glow = QRadialGradient(QPointF(W * 0.20, H * 0.68), 220)
        side_glow.setColorAt(0.0, QColor(sr.red(), sr.green(), sr.blue(), 22))
        side_glow.setColorAt(1.0, QColor(sr.red(), sr.green(), sr.blue(), 0))
        painter.fillRect(0, 0, W, H, side_glow)

        accent_line = QLinearGradient(0, 0, W, 0)
        accent_line.setColorAt(0.0, QColor(pr.red(), pr.green(), pr.blue(), 0))
        accent_line.setColorAt(0.22, QColor(pr.red(), pr.green(), pr.blue(), 185))
        accent_line.setColorAt(0.78, QColor(sr.red(), sr.green(), sr.blue(), 190))
        accent_line.setColorAt(1.0, QColor(sr.red(), sr.green(), sr.blue(), 0))
        painter.fillRect(QRectF(0, 0, W, 2), accent_line)

        for idx, alpha in enumerate((26, 18, 12), start=1):
            painter.setPen(QPen(QColor(sr.red(), sr.green(), sr.blue(), alpha), 1))
            inset = 26 + idx * 16
            painter.drawRoundedRect(QRectF(inset, 18 + idx * 10, W - inset * 2, 150 + idx * 16), 24, 24)

        badge_text = self._category.value.upper()
        badge_font = QFont(Font.SANS, 8)
        badge_font.setWeight(QFont.Weight.DemiBold)
        badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        painter.setFont(badge_font)
        badge_w = painter.fontMetrics().horizontalAdvance(badge_text) + 24
        badge_rect = QRectF((W - badge_w) / 2, 20, badge_w, 24)
        badge_path = QPainterPath()
        badge_path.addRoundedRect(badge_rect, 12, 12)
        painter.fillPath(badge_path, QColor(pr.red(), pr.green(), pr.blue(), 20))
        painter.setPen(QPen(QColor(pr.red(), pr.green(), pr.blue(), 82), 1))
        painter.drawPath(badge_path)
        painter.setPen(QColor(pr.red(), pr.green(), pr.blue(), 220))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        hero_rect = QRectF((W - 116) / 2, 56, 116, 116)
        hero_path = QPainterPath()
        hero_path.addRoundedRect(hero_rect, 30, 30)
        hero_grad = QLinearGradient(hero_rect.topLeft(), hero_rect.bottomRight())
        hero_grad.setColorAt(0.0, _mix(primary, "#FFFFFF", 0.12))
        hero_grad.setColorAt(1.0, _mix(primary, secondary, 0.42))
        painter.fillPath(hero_path, hero_grad)
        painter.setPen(QPen(_mix(primary, "#FFFFFF", 0.46), 1.4))
        painter.drawPath(hero_path)

        shine = QPainterPath()
        shine.addRoundedRect(
            QRectF(hero_rect.left() + 10, hero_rect.top() + 10, hero_rect.width() - 20, 26),
            13,
            13,
        )
        painter.fillPath(shine, QColor(255, 255, 255, 24))

        icon_size = 58
        hero_px = icon_pixmap(self._brand.icon_name, size=icon_size, color="#FFFFFF")
        painter.drawPixmap(int(hero_rect.center().x() - icon_size / 2), int(hero_rect.center().y() - icon_size / 2 - 2), hero_px)

        badge_size = 38
        badge_circle = QRectF(hero_rect.right() - badge_size * 0.74, hero_rect.bottom() - badge_size * 0.70, badge_size, badge_size)
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.4))
        painter.setBrush(QColor(secondary))
        painter.drawEllipse(badge_circle)
        badge_px = icon_pixmap(self._brand.badge_icon, size=18, color=primary)
        painter.drawPixmap(
            int(badge_circle.center().x() - badge_px.width() / 2),
            int(badge_circle.center().y() - badge_px.height() / 2),
            badge_px,
        )

        painter.setPen(QColor(_TEXT_BRIGHT))
        name_font = QFont(Font.SANS, 31)
        name_font.setWeight(QFont.Weight.Bold)
        name_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.6)
        painter.setFont(name_font)
        painter.drawText(QRect(0, 184, W, 40), Qt.AlignmentFlag.AlignCenter, self._app_name)

        painter.setPen(QColor(_TEXT_DIM))
        ver_font = QFont(Font.MONO, 10)
        painter.setFont(ver_font)
        painter.drawText(QRect(0, 217, W, 18), Qt.AlignmentFlag.AlignCenter, self._version)

        painter.setPen(QColor(_TEXT_MUTED))
        tag_font = QFont(Font.SANS, 11)
        painter.setFont(tag_font)
        painter.drawText(QRect(40, 238, W - 80, 20), Qt.AlignmentFlag.AlignCenter, self._brand.tagline)

        chip_font = QFont(Font.SANS, 9)
        chip_font.setWeight(QFont.Weight.Medium)
        painter.setFont(chip_font)
        spacing = 8
        chip_items = list(self._brand.features[:3])
        chip_widths = [painter.fontMetrics().horizontalAdvance(text) + 22 for text in chip_items]
        total_w = sum(chip_widths) + spacing * max(0, len(chip_widths) - 1)
        x = (W - total_w) / 2
        y = 268
        for idx, text in enumerate(chip_items):
            rect = QRectF(x, y, chip_widths[idx], 24)
            path = QPainterPath()
            path.addRoundedRect(rect, 12, 12)
            fill = QColor(pr.red(), pr.green(), pr.blue(), 18 if idx == 0 else 12)
            border = QColor(pr.red(), pr.green(), pr.blue(), 76 if idx == 0 else 52)
            painter.fillPath(path, fill)
            painter.setPen(QPen(border, 1))
            painter.drawPath(path)
            painter.setPen(QColor(_mix(primary, "#FFFFFF", 0.28)))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            x += chip_widths[idx] + spacing

        painter.setPen(QPen(QColor(_BORDER), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, W - 1, H - 1), 16, 16)
        painter.end()
        return pixmap

    def _render_pixmap(self) -> QPixmap:
        pixmap = QPixmap(self._static_base)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(_TRACK_BG))
        painter.drawRoundedRect(QRectF(_TRACK_MARGIN, _TRACK_Y, _TRACK_W, 4), 2, 2)

        fill_w = _TRACK_W * self._progress
        if fill_w > 0:
            pr = QColor(self._brand.primary)
            sr = QColor(self._brand.secondary)
            prog_grad = QLinearGradient(_TRACK_MARGIN, 0, _TRACK_MARGIN + fill_w, 0)
            prog_grad.setColorAt(0.0, QColor(pr.red(), pr.green(), pr.blue(), 235))
            prog_grad.setColorAt(1.0, QColor(sr.red(), sr.green(), sr.blue(), 220))
            painter.setBrush(prog_grad)
            painter.drawRoundedRect(QRectF(_TRACK_MARGIN, _TRACK_Y, fill_w, 4), 2, 2)

            if self._progress < 1.0:
                dot_x = _TRACK_MARGIN + fill_w
                painter.setBrush(QColor(pr.red(), pr.green(), pr.blue(), 86))
                painter.drawEllipse(QPointF(dot_x, _TRACK_Y + 2), 6, 6)

        painter.setPen(QColor(_TEXT_DIM))
        status_font = QFont(Font.SANS, 9)
        painter.setFont(status_font)
        painter.drawText(QRect(_TRACK_MARGIN, _TRACK_Y + 10, _TRACK_W // 2, 18), Qt.AlignmentFlag.AlignLeft, self._status_text)
        painter.drawText(QRect(W // 2, _TRACK_Y + 10, _TRACK_W // 2, 18), Qt.AlignmentFlag.AlignRight, f"{int(self._progress * 100)}%")
        painter.end()
        return pixmap
