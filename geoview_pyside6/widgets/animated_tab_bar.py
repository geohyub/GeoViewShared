"""
GeoView PySide6 — Animated Tab Bar
=====================================
언더라인 인디케이터가 선택된 탭으로 슬라이드하는 탭 바.
"""

from PySide6.QtWidgets import QTabBar, QFrame, QWidget
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt, QRect
from PySide6.QtGui import QColor

from geoview_pyside6.constants import Dark, Font, Space
from geoview_pyside6.theme_aware import c


class AnimatedTabBar(QTabBar):
    """언더라인 슬라이드 애니메이션이 있는 탭 바."""

    def __init__(self, accent: str = "", parent=None):
        super().__init__(parent)
        self._accent = accent or c().CYAN

        # Indicator line
        self._indicator = QFrame(self)
        self._indicator.setFixedHeight(2)
        self._indicator.setStyleSheet(f"background: {self._accent}; border-radius: 1px;")

        # Animation
        self._anim = QPropertyAnimation(self._indicator, b"geometry", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.currentChanged.connect(self._animate_to_tab)

        # Style the tab bar itself
        self.setStyleSheet(f"""
            QTabBar {{
                background: transparent;
                border: none;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {c().DIM};
                padding: 8px {Space.LG}px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: {Font.SM}px;
                font-family: {Font.SANS};
            }}
            QTabBar::tab:hover {{
                color: {c().TEXT};
            }}
            QTabBar::tab:selected {{
                color: {self._accent};
                font-weight: {Font.MEDIUM};
                border-bottom: 2px solid transparent;
            }}
        """)

    def _animate_to_tab(self, index: int):
        if index < 0 or index >= self.count():
            return
        rect = self.tabRect(index)
        target = QRect(rect.x(), self.height() - 2, rect.width(), 2)

        if not self._indicator.isVisible():
            self._indicator.setGeometry(target)
            self._indicator.show()
        else:
            self._anim.stop()
            self._anim.setStartValue(self._indicator.geometry())
            self._anim.setEndValue(target)
            self._anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reposition indicator to current tab
        idx = self.currentIndex()
        if idx >= 0:
            rect = self.tabRect(idx)
            self._indicator.setGeometry(rect.x(), self.height() - 2, rect.width(), 2)

    def showEvent(self, event):
        super().showEvent(event)
        idx = self.currentIndex()
        if idx >= 0:
            self._animate_to_tab(idx)
