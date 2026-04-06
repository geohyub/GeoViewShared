"""
GeoView PySide6 — Utilities
=============================
텍스트 말줄임, 숫자 포맷 등 공통 유틸리티.
"""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics


def elided_text(text: str, metrics: QFontMetrics, max_width: int,
                mode=Qt.TextElideMode.ElideRight) -> str:
    """QFontMetrics 기반 말줄임 처리. 폭 초과 시 '...' 추가."""
    return metrics.elidedText(text, mode, max_width)


class ElidedLabel(QLabel):
    """자동 말줄임 라벨. 폭이 부족하면 ... 표시."""

    def __init__(self, text: str = "", parent=None,
                 elide_mode=Qt.TextElideMode.ElideRight):
        super().__init__(text, parent)
        self._full_text = text
        self._elide_mode = elide_mode

    def setText(self, text: str):
        self._full_text = text
        self._update_elision()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elision()

    def _update_elision(self):
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full_text, self._elide_mode,
                                     self.width() - 4)  # 4px margin
        super().setText(elided)
        if elided != self._full_text:
            self.setToolTip(self._full_text)
        else:
            self.setToolTip("")

    def full_text(self) -> str:
        return self._full_text
