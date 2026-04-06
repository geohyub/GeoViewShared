"""
GeoView PySide6 — Help & Tooltip System
==========================================
위젯에 툴팁 + 상태바 팁을 동시에 설정하는 유틸리티.
"""

from PySide6.QtWidgets import QWidget


def set_help(widget: QWidget, tooltip: str, status_tip: str = "") -> None:
    """위젯에 툴팁 + 상태바 팁 동시 설정.

    Args:
        widget: 대상 위젯
        tooltip: 마우스 호버 시 표시할 툴팁 텍스트
        status_tip: 상태바에 표시할 설명 텍스트 (비어 있으면 설정 안 함)
    """
    widget.setToolTip(tooltip)
    if status_tip:
        widget.setStatusTip(status_tip)
