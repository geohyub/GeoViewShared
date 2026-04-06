"""
GeoView PySide6 — Busy State Utilities
========================================
장시간 작업 시 WaitCursor + 위젯 비활성화 관리.
"""

from contextlib import contextmanager
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt


@contextmanager
def busy_cursor():
    """장시간 작업 시 WaitCursor 표시. with 문 사용."""
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


class BusyGuard:
    """위젯 비활성화 + WaitCursor를 동시에 관리하는 컨텍스트 매니저.

    Usage::
        with BusyGuard(self.export_btn, self.analyze_btn):
            heavy_computation()
    """
    def __init__(self, *widgets: QWidget):
        self._widgets = widgets

    def __enter__(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        for w in self._widgets:
            w.setEnabled(False)
        QApplication.processEvents()
        return self

    def __exit__(self, *args):
        for w in self._widgets:
            w.setEnabled(True)
        QApplication.restoreOverrideCursor()
