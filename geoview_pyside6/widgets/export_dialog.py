"""
GeoView Export Progress Dialog
================================
Shows export progress with status messages and completion feedback.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QFrame, QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from geoview_pyside6.constants import Font, Space, Radius
from geoview_pyside6.theme_aware import c


class ExportProgressDialog(QDialog):
    """Modal dialog showing export progress."""

    def __init__(self, title: str = "Exporting...", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(460, 200)
        self.setStyleSheet(f"""
            QDialog {{
                background: {c().BG};
                color: {c().TEXT};
                border: 1px solid {c().BORDER};
                border-radius: {Radius.BASE}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(Space.MD)
        layout.setContentsMargins(Space.XL, Space.XL, Space.XL, Space.XL)

        # Title
        self._title = QLabel(title)
        self._title.setStyleSheet(f"""
            color: {c().TEXT_BRIGHT};
            font-size: {Font.MD}px;
            font-weight: {Font.SEMIBOLD};
            background: transparent;
        """)
        layout.addWidget(self._title)

        # Status message
        self._status = QLabel("Preparing...")
        self._status.setStyleSheet(f"""
            color: {c().MUTED};
            font-size: {Font.SM}px;
            background: transparent;
        """)
        layout.addWidget(self._status)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        # Percent
        self._percent = QLabel("0%")
        self._percent.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._percent.setStyleSheet(f"""
            color: {c().DIM};
            font-size: {Font.XS}px;
            background: transparent;
        """)
        layout.addWidget(self._percent)

        layout.addStretch()

        # Button row
        self._btn_layout = QHBoxLayout()
        self._btn_layout.setSpacing(Space.SM)
        self._btn_layout.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("secondaryButton")
        self._cancel_btn.clicked.connect(self.reject)
        self._btn_layout.addWidget(self._cancel_btn)

        layout.addLayout(self._btn_layout)

    def showEvent(self, event):
        super().showEvent(event)
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        self._fade = QPropertyAnimation(effect, b"opacity", self)
        self._fade.setDuration(150)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(lambda: self.setGraphicsEffect(None))
        self._fade.start()

    def update_progress(self, percent: int, message: str = ""):
        self._progress.setValue(percent)
        self._percent.setText(f"{percent}%")
        if message:
            self._status.setText(message)

    def set_finished(self, message: str = "Complete!", file_path: str = ""):
        self._progress.setValue(100)
        self._percent.setText("100%")
        self._status.setText(message)
        self._status.setStyleSheet(f"""
            color: {c().GREEN};
            font-size: {Font.SM}px;
            background: transparent;
        """)
        self._cancel_btn.setText("Close")

        if file_path:
            import os
            folder = os.path.dirname(os.path.abspath(file_path))
            open_btn = QPushButton("Open Folder")
            open_btn.setObjectName("secondaryButton")
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.clicked.connect(lambda: self._open_folder(folder))
            # Insert before the Close button
            idx = self._btn_layout.indexOf(self._cancel_btn)
            self._btn_layout.insertWidget(idx, open_btn)

        QTimer.singleShot(2000, self.accept)

    def _open_folder(self, folder: str):
        """Open the containing folder in the system file manager."""
        import subprocess
        import sys as _sys
        if _sys.platform == "win32":
            subprocess.Popen(f'explorer "{folder}"')
        elif _sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def set_error(self, message: str):
        self._status.setText(message)
        self._status.setStyleSheet(f"""
            color: {c().RED};
            font-size: {Font.SM}px;
            background: transparent;
        """)
        self._cancel_btn.setText("Close")
