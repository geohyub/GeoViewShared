"""
GeoView — Splash Screen v2
============================
Professional branded splash with gradient, glow, progress bar, and blur-safe text.
All 22 apps share this. Always renders in dark mode for brand consistency.
"""

from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QLinearGradient,
    QRadialGradient, QPen, QPainterPath, QBrush,
)
from PySide6.QtCore import Qt, QRect, QRectF, QTimer, QPointF

from geoview_pyside6.constants import Category, CATEGORY_THEMES, Font


# ── Dark palette (splash always dark for brand consistency) ──
_BG_TOP = "#0c0c0e"
_BG_BOT = "#141418"
_TEXT_BRIGHT = "#f5f5f5"
_TEXT_MUTED = "#8b8b92"
_TEXT_DIM = "#5a5a60"
_BORDER = "#252528"


def _create_splash_pixmap(app_name: str, version: str, category: Category) -> QPixmap:
    """540x320 modern splash screen."""
    W, H = 540, 320
    theme = CATEGORY_THEMES.get(category, CATEGORY_THEMES[Category.PROCESSING])
    accent = theme.accent

    pixmap = QPixmap(W, H)
    pixmap.fill(QColor(_BG_TOP))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # ── Background: subtle vertical gradient ──
    bg_grad = QLinearGradient(0, 0, 0, H)
    bg_grad.setColorAt(0.0, QColor(_BG_TOP))
    bg_grad.setColorAt(1.0, QColor(_BG_BOT))
    painter.fillRect(0, 0, W, H, bg_grad)

    # ── Accent glow: large radial at top-center ──
    ar, ag, ab = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    glow = QRadialGradient(QPointF(W / 2, -20), 280)
    glow.setColorAt(0.0, QColor(ar, ag, ab, 30))
    glow.setColorAt(0.5, QColor(ar, ag, ab, 8))
    glow.setColorAt(1.0, QColor(ar, ag, ab, 0))
    painter.fillRect(0, 0, W, 160, glow)

    # ── Top accent line (2px) ──
    painter.setPen(Qt.PenStyle.NoPen)
    accent_grad = QLinearGradient(0, 0, W, 0)
    accent_grad.setColorAt(0.0, QColor(ar, ag, ab, 0))
    accent_grad.setColorAt(0.3, QColor(ar, ag, ab, 180))
    accent_grad.setColorAt(0.7, QColor(ar, ag, ab, 180))
    accent_grad.setColorAt(1.0, QColor(ar, ag, ab, 0))
    painter.setBrush(accent_grad)
    painter.drawRect(0, 0, W, 2)

    # ── Category badge (small pill) ──
    badge_text = category.value.upper()
    badge_font = QFont(Font.SANS, 8)
    badge_font.setWeight(QFont.Weight.DemiBold)
    badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
    painter.setFont(badge_font)
    badge_w = painter.fontMetrics().horizontalAdvance(badge_text) + 20
    badge_h = 22
    badge_x = (W - badge_w) / 2
    badge_y = 75

    # Badge background (accent dim)
    badge_path = QPainterPath()
    badge_path.addRoundedRect(QRectF(badge_x, badge_y, badge_w, badge_h), 11, 11)
    painter.fillPath(badge_path, QColor(ar, ag, ab, 25))
    painter.setPen(QColor(ar, ag, ab, 60))
    painter.drawPath(badge_path)

    painter.setPen(QColor(ar, ag, ab, 200))
    painter.drawText(QRectF(badge_x, badge_y, badge_w, badge_h),
                     Qt.AlignmentFlag.AlignCenter, badge_text)

    # ── App name (hero text) ──
    painter.setPen(QColor(_TEXT_BRIGHT))
    name_font = QFont(Font.SANS, 32)
    name_font.setWeight(QFont.Weight.Bold)
    name_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -1.0)
    painter.setFont(name_font)
    painter.drawText(QRect(0, 108, W, 48), Qt.AlignmentFlag.AlignCenter, app_name)

    # ── Version ──
    painter.setPen(QColor(_TEXT_DIM))
    ver_font = QFont(Font.MONO, 11)
    painter.setFont(ver_font)
    painter.drawText(QRect(0, 160, W, 22), Qt.AlignmentFlag.AlignCenter, version)

    # ── Subtitle ──
    painter.setPen(QColor(_TEXT_MUTED))
    sub_font = QFont(Font.SANS, 10)
    sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
    painter.setFont(sub_font)
    painter.drawText(QRect(0, 186, W, 20), Qt.AlignmentFlag.AlignCenter, "GeoView Suite")

    # ── Bottom section: progress track + status ──
    # Track background (thin line)
    track_y = H - 38
    track_margin = 40
    track_w = W - track_margin * 2
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(_BORDER))
    painter.drawRoundedRect(QRectF(track_margin, track_y, track_w, 3), 1.5, 1.5)

    # Progress fill (accent, 30% initial)
    fill_w = track_w * 0.3
    prog_grad = QLinearGradient(track_margin, 0, track_margin + fill_w, 0)
    prog_grad.setColorAt(0.0, QColor(ar, ag, ab, 200))
    prog_grad.setColorAt(1.0, QColor(ar, ag, ab, 120))
    painter.setBrush(prog_grad)
    painter.drawRoundedRect(QRectF(track_margin, track_y, fill_w, 3), 1.5, 1.5)

    # Status text placeholder
    painter.setPen(QColor(_TEXT_DIM))
    status_font = QFont(Font.SANS, 9)
    painter.setFont(status_font)
    painter.drawText(QRect(track_margin, track_y + 8, track_w, 18),
                     Qt.AlignmentFlag.AlignLeft, "Loading...")

    # ── Border (subtle) ──
    painter.setPen(QPen(QColor(_BORDER), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(0.5, 0.5, W - 1, H - 1), 12, 12)

    painter.end()

    # Apply rounded corners mask
    mask = QPixmap(W, H)
    mask.fill(QColor(0, 0, 0, 0))
    mask_painter = QPainter(mask)
    mask_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    mask_painter.setBrush(QColor(255, 255, 255))
    mask_painter.setPen(Qt.PenStyle.NoPen)
    mask_painter.drawRoundedRect(QRectF(0, 0, W, H), 12, 12)
    mask_painter.end()

    # Compose with mask
    result = QPixmap(W, H)
    result.fill(QColor(0, 0, 0, 0))
    rp = QPainter(result)
    rp.setRenderHint(QPainter.RenderHint.Antialiasing)
    rp.drawPixmap(0, 0, mask)
    rp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    rp.drawPixmap(0, 0, pixmap)
    rp.end()

    return result


class GeoViewSplash(QSplashScreen):
    """GeoView branded splash screen v2."""

    def __init__(self, app_name: str, version: str = "",
                 category: Category = Category.PROCESSING):
        pixmap = _create_splash_pixmap(app_name, version, category)
        super().__init__(pixmap)
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._app_name = app_name

    def set_status(self, message: str):
        """Update bottom status message."""
        self.showMessage(
            message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            QColor(_TEXT_DIM),
        )

    def finish_with_delay(self, window, delay_ms: int = 800):
        """Close splash after delay and show main window."""
        QTimer.singleShot(delay_ms, lambda: self._finish(window))

    def _finish(self, window):
        self.finish(window)
