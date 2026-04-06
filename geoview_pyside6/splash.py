"""
GeoView — Splash Screen
=========================
앱 시작 시 표시되는 브랜드 스플래시 스크린.
"""

from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient
from PySide6.QtCore import Qt, QRect, QTimer

from geoview_pyside6.constants import Category, CATEGORY_THEMES, Font
from geoview_pyside6.theme_aware import c


def _create_splash_pixmap(app_name: str, version: str, category: Category) -> QPixmap:
    """400x240 스플래시 스크린 이미지 생성."""
    W, H = 480, 280
    theme = CATEGORY_THEMES.get(category, CATEGORY_THEMES[Category.PROCESSING])

    pixmap = QPixmap(W, H)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background gradient (dark → slightly lighter)
    gradient = QLinearGradient(0, 0, W, H)
    gradient.setColorAt(0.0, QColor(c().BG))
    gradient.setColorAt(1.0, QColor(c().BG_ALT))
    painter.fillRect(0, 0, W, H, gradient)

    # Subtle accent glow at top center
    glow = QLinearGradient(W/2 - 100, 0, W/2 + 100, 60)
    glow.setColorAt(0.0, QColor(theme.accent + "00"))  # transparent
    glow.setColorAt(0.5, QColor(theme.accent + "15"))  # subtle
    glow.setColorAt(1.0, QColor(theme.accent + "00"))
    painter.fillRect(0, 0, W, 60, glow)

    # App name
    painter.setPen(QColor(theme.accent))
    name_font = QFont(Font.SANS, 28)
    name_font.setWeight(QFont.Weight.Bold)
    painter.setFont(name_font)
    painter.drawText(QRect(0, 70, W, 50), Qt.AlignmentFlag.AlignCenter, app_name)

    # Version
    painter.setPen(QColor(c().DIM))
    ver_font = QFont(Font.SANS, 12)
    painter.setFont(ver_font)
    painter.drawText(QRect(0, 120, W, 25), Qt.AlignmentFlag.AlignCenter, version)

    # "GeoView Suite" subtitle
    painter.setPen(QColor(c().MUTED))
    sub_font = QFont(Font.SANS, 10)
    painter.setFont(sub_font)
    painter.drawText(QRect(0, 148, W, 20), Qt.AlignmentFlag.AlignCenter, "GeoView Suite")

    # Bottom bar area for status message
    painter.setPen(QColor(c().DIM))
    status_font = QFont(Font.SANS, 9)
    painter.setFont(status_font)
    painter.drawText(QRect(20, H - 35, W - 40, 20), Qt.AlignmentFlag.AlignLeft, "Loading...")

    # Bottom line accent
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(theme.accent))
    painter.drawRect(0, H - 3, W, 3)

    painter.end()
    return pixmap


class GeoViewSplash(QSplashScreen):
    """GeoView 브랜드 스플래시 스크린."""

    def __init__(self, app_name: str, version: str = "",
                 category: Category = Category.PROCESSING):
        pixmap = _create_splash_pixmap(app_name, version, category)
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint)
        self._app_name = app_name

    def set_status(self, message: str):
        """하단 상태 메시지 갱신."""
        self.showMessage(
            message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
            QColor(c().DIM),
        )

    def finish_with_delay(self, window, delay_ms: int = 800):
        """delay 후에 스플래시 닫고 메인 윈도우 표시."""
        QTimer.singleShot(delay_ms, lambda: self._finish(window))

    def _finish(self, window):
        self.finish(window)
