"""
GeoView Confirm Dialog
========================
Themed confirmation dialog replacing QMessageBox.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from geoview_pyside6.constants import Font, Space, Radius
from geoview_pyside6.theme_aware import c


class ConfirmDialog(QDialog):
    """Themed confirmation dialog."""

    @staticmethod
    def _get_icons() -> dict:
        return {
            "info": ("\u2139", c().CYAN),
            "warning": ("\u26a0", c().ORANGE),
            "error": ("\u2717", c().RED),
            "success": ("\u2713", c().GREEN),
        }

    def __init__(self, title: str, message: str,
                 confirm_text: str = "Confirm",
                 cancel_text: str = "Cancel",
                 dialog_type: str = "info",
                 parent=None):
        super().__init__(parent)
        self._dialog_type = dialog_type
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setStyleSheet(f"""
            QDialog {{
                background: {c().BG};
                color: {c().TEXT};
            }}
        """)

        icons = self._get_icons()
        icon_char, icon_color = icons.get(dialog_type, icons["info"])

        layout = QVBoxLayout(self)
        layout.setSpacing(Space.BASE)
        layout.setContentsMargins(Space.XL, Space.XL, Space.XL, Space.XL)

        # Header row (icon + title)
        header = QHBoxLayout()
        icon_label = QLabel(icon_char)
        icon_label.setFixedSize(36, 36)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            font-size: 18px;
            color: {icon_color};
            background: {icon_color}1A;
            border-radius: {Radius.SM}px;
            border: none;
        """)
        header.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {c().TEXT_BRIGHT};
            font-size: {Font.MD}px;
            font-weight: {Font.SEMIBOLD};
            background: transparent;
            border: none;
        """)
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            color: {c().TEXT};
            font-size: {Font.BASE}px;
            padding: {Space.SM}px 0;
            background: transparent;
            border: none;
        """)
        layout.addWidget(msg_label)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if cancel_text:
            cancel_btn = QPushButton(cancel_text)
            cancel_btn.setObjectName("secondaryButton")
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_text)
        if dialog_type == "error":
            confirm_btn.setStyleSheet(f"""
                background: {c().RED};
                color: white;
                border: none;
                border-radius: {Radius.SM}px;
                padding: {Space.SM}px {Space.BASE}px;
                font-weight: {Font.SEMIBOLD};
            """)
        else:
            confirm_btn.setObjectName("primaryButton")
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

    def showEvent(self, event):
        super().showEvent(event)
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        self._fade_anim = QPropertyAnimation(effect, b"opacity", self)
        self._fade_anim.setDuration(150)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(lambda: self.setGraphicsEffect(None))
        self._fade_anim.start()

        # Shake for error type
        if self._dialog_type == "error":
            QTimer.singleShot(200, self._shake)  # After fade-in
            try:
                from geoview_pyside6.sounds import play
                play("error")
            except Exception:
                pass

    def _shake(self):
        """Left-right shake animation (3 oscillations)."""
        orig_x = self.x()
        self._shake_step = 0
        self._shake_orig = orig_x
        self._shake_timer = QTimer(self)
        self._shake_timer.setInterval(40)
        self._shake_timer.timeout.connect(self._shake_tick)
        self._shake_timer.start()

    def _shake_tick(self):
        offsets = [6, -6, 4, -4, 2, -2, 0]
        if self._shake_step < len(offsets):
            self.move(self._shake_orig + offsets[self._shake_step], self.y())
            self._shake_step += 1
        else:
            self._shake_timer.stop()
            self.move(self._shake_orig, self.y())
