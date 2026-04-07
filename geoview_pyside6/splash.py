"""
GeoView — Splash Screen v3
============================
Animated splash with live progress bar that fills during app initialization.
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
_TRACK_BG = "#252528"

W, H = 540, 320
_TRACK_Y = H - 38
_TRACK_MARGIN = 40
_TRACK_W = W - _TRACK_MARGIN * 2


class GeoViewSplash(QSplashScreen):
    """GeoView branded splash with animated progress bar."""

    def __init__(self, app_name: str, version: str = "",
                 category: Category = Category.PROCESSING):
        self._app_name = app_name
        self._version = version
        self._category = category
        self._theme = CATEGORY_THEMES.get(category, CATEGORY_THEMES[Category.PROCESSING])
        self._progress = 0.0  # 0.0 ~ 1.0
        self._status_text = "Loading..."
        self._accent_r = int(self._theme.accent[1:3], 16)
        self._accent_g = int(self._theme.accent[3:5], 16)
        self._accent_b = int(self._theme.accent[5:7], 16)

        # Create initial pixmap
        pixmap = self._render_pixmap()
        super().__init__(pixmap)
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Auto-advance animation (smooth fill during init)
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(30)
        self._auto_timer.timeout.connect(self._auto_advance)
        self._auto_timer.start()

    def _auto_advance(self):
        """Smoothly advance progress bar during initialization."""
        if self._progress < 0.85:
            # Fast at first, slows down approaching 85%
            remaining = 0.85 - self._progress
            self._progress += remaining * 0.08
            self._update_pixmap()

    def set_status(self, message: str):
        """Update status text and repaint."""
        self._status_text = message
        if message.lower() in ("ready", "done", "완료"):
            self._progress = 1.0
            self._auto_timer.stop()
        self._update_pixmap()
        QApplication.processEvents()

    def set_progress(self, value: float):
        """Set progress 0.0~1.0 directly."""
        self._progress = max(0.0, min(1.0, value))
        self._update_pixmap()

    def finish_with_delay(self, window, delay_ms: int = 600):
        """Fill to 100%, then close after delay."""
        self._progress = 1.0
        self._auto_timer.stop()
        self._update_pixmap()
        QTimer.singleShot(delay_ms, lambda: self._finish(window))

    def _finish(self, window):
        self.finish(window)

    def _update_pixmap(self):
        """Re-render and update the splash pixmap."""
        self.setPixmap(self._render_pixmap())
        self.repaint()

    def _render_pixmap(self) -> QPixmap:
        """Render the full splash image with current progress."""
        accent = self._theme.accent
        ar, ag, ab = self._accent_r, self._accent_g, self._accent_b

        pixmap = QPixmap(W, H)
        pixmap.fill(QColor(_BG_TOP))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background gradient
        bg_grad = QLinearGradient(0, 0, 0, H)
        bg_grad.setColorAt(0.0, QColor(_BG_TOP))
        bg_grad.setColorAt(1.0, QColor(_BG_BOT))
        painter.fillRect(0, 0, W, H, bg_grad)

        # Accent glow at top
        glow = QRadialGradient(QPointF(W / 2, -20), 280)
        glow.setColorAt(0.0, QColor(ar, ag, ab, 30))
        glow.setColorAt(0.5, QColor(ar, ag, ab, 8))
        glow.setColorAt(1.0, QColor(ar, ag, ab, 0))
        painter.fillRect(0, 0, W, 160, glow)

        # Top accent line
        accent_grad = QLinearGradient(0, 0, W, 0)
        accent_grad.setColorAt(0.0, QColor(ar, ag, ab, 0))
        accent_grad.setColorAt(0.3, QColor(ar, ag, ab, 180))
        accent_grad.setColorAt(0.7, QColor(ar, ag, ab, 180))
        accent_grad.setColorAt(1.0, QColor(ar, ag, ab, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent_grad)
        painter.drawRect(0, 0, W, 2)

        # Category badge
        badge_text = self._category.value.upper()
        badge_font = QFont(Font.SANS, 8)
        badge_font.setWeight(QFont.Weight.DemiBold)
        badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        painter.setFont(badge_font)
        badge_w = painter.fontMetrics().horizontalAdvance(badge_text) + 20
        badge_h = 22
        badge_x = (W - badge_w) / 2
        badge_y = 75
        badge_path = QPainterPath()
        badge_path.addRoundedRect(QRectF(badge_x, badge_y, badge_w, badge_h), 11, 11)
        painter.fillPath(badge_path, QColor(ar, ag, ab, 25))
        painter.setPen(QColor(ar, ag, ab, 60))
        painter.drawPath(badge_path)
        painter.setPen(QColor(ar, ag, ab, 200))
        painter.drawText(QRectF(badge_x, badge_y, badge_w, badge_h),
                         Qt.AlignmentFlag.AlignCenter, badge_text)

        # App name
        painter.setPen(QColor(_TEXT_BRIGHT))
        name_font = QFont(Font.SANS, 32)
        name_font.setWeight(QFont.Weight.Bold)
        name_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -1.0)
        painter.setFont(name_font)
        painter.drawText(QRect(0, 108, W, 48), Qt.AlignmentFlag.AlignCenter, self._app_name)

        # Version
        painter.setPen(QColor(_TEXT_DIM))
        ver_font = QFont(Font.MONO, 11)
        painter.setFont(ver_font)
        painter.drawText(QRect(0, 160, W, 22), Qt.AlignmentFlag.AlignCenter, self._version)

        # Subtitle
        painter.setPen(QColor(_TEXT_MUTED))
        sub_font = QFont(Font.SANS, 10)
        sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        painter.setFont(sub_font)
        painter.drawText(QRect(0, 186, W, 20), Qt.AlignmentFlag.AlignCenter, "GeoView Suite")

        # ── Progress bar (animated) ──
        # Track background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(_TRACK_BG))
        painter.drawRoundedRect(QRectF(_TRACK_MARGIN, _TRACK_Y, _TRACK_W, 3), 1.5, 1.5)

        # Progress fill
        fill_w = _TRACK_W * self._progress
        if fill_w > 0:
            prog_grad = QLinearGradient(_TRACK_MARGIN, 0, _TRACK_MARGIN + fill_w, 0)
            prog_grad.setColorAt(0.0, QColor(ar, ag, ab, 220))
            prog_grad.setColorAt(1.0, QColor(ar, ag, ab, 140))
            painter.setBrush(prog_grad)
            painter.drawRoundedRect(
                QRectF(_TRACK_MARGIN, _TRACK_Y, fill_w, 3), 1.5, 1.5)

            # Glow dot at the leading edge
            if self._progress < 1.0:
                dot_x = _TRACK_MARGIN + fill_w
                painter.setBrush(QColor(ar, ag, ab, 80))
                painter.drawEllipse(QPointF(dot_x, _TRACK_Y + 1.5), 6, 6)

        # Status text
        painter.setPen(QColor(_TEXT_DIM))
        status_font = QFont(Font.SANS, 9)
        painter.setFont(status_font)
        painter.drawText(QRect(_TRACK_MARGIN, _TRACK_Y + 8, _TRACK_W // 2, 18),
                         Qt.AlignmentFlag.AlignLeft, self._status_text)

        # Percentage
        pct_text = f"{int(self._progress * 100)}%"
        painter.drawText(QRect(W // 2, _TRACK_Y + 8, _TRACK_W // 2, 18),
                         Qt.AlignmentFlag.AlignRight, pct_text)

        # Border
        painter.setPen(QPen(QColor(_BORDER), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, W - 1, H - 1), 12, 12)

        painter.end()

        # Rounded corners mask
        mask = QPixmap(W, H)
        mask.fill(QColor(0, 0, 0, 0))
        mp = QPainter(mask)
        mp.setRenderHint(QPainter.RenderHint.Antialiasing)
        mp.setBrush(QColor(255, 255, 255))
        mp.setPen(Qt.PenStyle.NoPen)
        mp.drawRoundedRect(QRectF(0, 0, W, H), 12, 12)
        mp.end()

        result = QPixmap(W, H)
        result.fill(QColor(0, 0, 0, 0))
        rp = QPainter(result)
        rp.setRenderHint(QPainter.RenderHint.Antialiasing)
        rp.drawPixmap(0, 0, mask)
        rp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        rp.drawPixmap(0, 0, pixmap)
        rp.end()

        return result
