"""Success celebration overlay -- animated checkmark + message."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QColor
from geoview_pyside6.constants import Font


class _CheckmarkWidget(QWidget):
    """Checkmark stroke animation widget."""

    def __init__(self, color: str = "#10B981", size: int = 64, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor(color)
        self._progress = 0.0  # 0.0 -> 1.0
        self._size = size

    def set_progress(self, p: float):
        self._progress = p
        self.update()

    progress = property(lambda self: self._progress, set_progress)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._size
        cx, cy = s / 2, s / 2
        r = s / 2 - 4

        # Circle background
        painter.setPen(Qt.PenStyle.NoPen)
        bg = QColor(self._color)
        bg.setAlpha(30)
        painter.setBrush(bg)
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Circle border (progress-based)
        if self._progress > 0:
            pen = QPen(self._color, 3)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            span = int(-self._progress * 360 * 16)
            painter.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 90 * 16, span)

        # Checkmark (draws after circle is 60% done)
        if self._progress > 0.6:
            check_p = (self._progress - 0.6) / 0.4  # 0->1 within last 40%
            pen = QPen(self._color, 3.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            # Checkmark points (relative to center)
            p1 = QPointF(cx - r * 0.3, cy)
            p2 = QPointF(cx - r * 0.05, cy + r * 0.3)
            p3 = QPointF(cx + r * 0.35, cy - r * 0.25)

            if check_p <= 0.5:
                # First stroke (p1 -> p2)
                t = check_p * 2
                mid = QPointF(
                    p1.x() + (p2.x() - p1.x()) * t,
                    p1.y() + (p2.y() - p1.y()) * t,
                )
                painter.drawLine(p1, mid)
            else:
                # Full first stroke + partial second
                painter.drawLine(p1, p2)
                t = (check_p - 0.5) * 2
                mid = QPointF(
                    p2.x() + (p3.x() - p2.x()) * t,
                    p2.y() + (p3.y() - p2.y()) * t,
                )
                painter.drawLine(p2, mid)

        painter.end()


class SuccessOverlay(QWidget):
    """Success celebration overlay -- checkmark drawing + message."""

    def __init__(self, message: str = "Complete!", color: str = "#10B981",
                 duration: int = 2000, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: rgba(10, 14, 23, 180);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._check = _CheckmarkWidget(color, 64, self)
        layout.addWidget(self._check, 0, Qt.AlignmentFlag.AlignCenter)

        self._msg = QLabel(message)
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg.setStyleSheet(f"""
            color: {color};
            font-size: {Font.MD}px;
            font-weight: {Font.MEDIUM};
            background: transparent;
            padding-top: 12px;
        """)
        self._msg.setVisible(False)
        layout.addWidget(self._msg, 0, Qt.AlignmentFlag.AlignCenter)

        self._duration = duration

    def show_success(self):
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.raise_()
        self.show()

        # Play sound
        try:
            from geoview_pyside6.sounds import play
            play("success")
        except Exception:
            pass

        # Animate checkmark (500ms)
        self._anim = QPropertyAnimation(self._check, b"progress")
        self._anim.setDuration(500)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(lambda: self._msg.setVisible(True))
        self._anim.start()

        # Auto-dismiss
        QTimer.singleShot(self._duration, self._fade_out)

    def _fade_out(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(300)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.finished.connect(self.deleteLater)
        fade.start()
        # Must keep reference alive
        self._fade_anim = fade
