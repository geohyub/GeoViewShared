"""
GeoView PySide6 — Loading Spinner & Overlay
=============================================
원형 도트 회전 스피너 + 반투명 로딩 오버레이.
"""

import math
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QSize, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from geoview_pyside6.constants import Font, Space
from geoview_pyside6.theme_aware import c


class LoadingSpinner(QWidget):
    """원형 로딩 스피너 — 8개 도트가 시계 방향으로 회전."""

    def __init__(self, size: int = 40, color: str | None = None, parent=None):
        super().__init__(parent)
        self._size = size
        self._color = QColor(color) if color else QColor(c().MUTED)
        self._dot_count = 8
        self._current_step = 0
        self._dot_radius = max(2, size // 12)

        self.setFixedSize(QSize(size, size))

        self._timer = QTimer(self)
        self._timer.setInterval(80)  # ~12.5 fps rotation
        self._timer.timeout.connect(self._advance)

    def start(self):
        self._current_step = 0
        self._timer.start()
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _advance(self):
        self._current_step = (self._current_step + 1) % self._dot_count
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPointF(self._size / 2, self._size / 2)
        orbit_r = (self._size - self._dot_radius * 4) / 2

        for i in range(self._dot_count):
            # Angle for this dot (starting from top, clockwise)
            angle = (2 * math.pi / self._dot_count) * i - math.pi / 2
            x = center.x() + orbit_r * math.cos(angle)
            y = center.y() + orbit_r * math.sin(angle)

            # Opacity: highest at current_step, fading for trailing dots
            steps_behind = (self._current_step - i) % self._dot_count
            opacity = max(0.15, 1.0 - steps_behind * (0.85 / self._dot_count))

            color = QColor(self._color)
            color.setAlphaF(opacity)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x, y), self._dot_radius, self._dot_radius)

        painter.end()


class LoadingOverlay(QFrame):
    """반투명 오버레이 + 중앙 스피너 + 선택적 메시지.

    부모 위젯 위에 겹쳐서 표시. show_loading/hide_loading으로 제어.
    """

    def __init__(self, message: str = "", color: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingOverlay")

        # Fill parent completely
        self.setStyleSheet(f"""
            #loadingOverlay {{
                background-color: rgba(10, 14, 23, 200);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._spinner = LoadingSpinner(size=48, color=color, parent=self)
        layout.addWidget(self._spinner, 0, Qt.AlignmentFlag.AlignCenter)

        self._message = QLabel(message)
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setStyleSheet(f"""
            color: {c().MUTED};
            font-size: {Font.SM}px;
            font-family: {Font.SANS};
            background: transparent;
            padding-top: {Space.SM}px;
        """)
        if not message:
            self._message.hide()
        layout.addWidget(self._message, 0, Qt.AlignmentFlag.AlignCenter)

        self.hide()

    def show_loading(self, message: str = ""):
        if message:
            self._message.setText(message)
            self._message.show()
        elif not self._message.text():
            self._message.hide()

        # Resize to fill parent
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.raise_()
        self.show()
        self._spinner.start()

    def hide_loading(self):
        self._spinner.stop()
        self.hide()

    def resizeEvent(self, event):
        """부모 리사이즈 시 오버레이도 리사이즈."""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)
