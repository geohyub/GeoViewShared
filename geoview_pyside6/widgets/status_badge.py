"""
Status Badge Widget
====================
PASS/WARN/FAIL/INFO 상태를 색상 배지로 표시.
색맹 접근성을 위해 상태 아이콘 프리픽스 지원.
"""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class StatusBadge(QLabel):
    """
    상태 배지.

    Usage:
        badge = StatusBadge("PASS")              # shows "✓ PASS"
        badge = StatusBadge("FAIL")              # shows "✗ FAIL"
        badge = StatusBadge("A", badge_type="grade")  # shows "A" (no icon)
        badge = StatusBadge("PASS", show_icon=False)  # shows "PASS" (icon disabled)
    """

    STYLE_MAP = {
        "PASS": "badgePass",
        "WARN": "badgeWarn",
        "FAIL": "badgeFail",
        "INFO": "badgeInfo",
        "A": "badgePass",
        "B": "badgeWarn",
        "C": "badgeWarn",
        "D": "badgeFail",
    }

    ICON_MAP = {
        "PASS": "\u2713",  # checkmark
        "WARN": "\u26A0",  # warning sign
        "FAIL": "\u2717",  # ballot x
        "INFO": "\u2139",  # information source
    }

    def __init__(self, text: str = "", parent=None, *, show_icon: bool = True):
        self._show_icon = show_icon
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_status(text)

    def update_status(self, text: str):
        key = text.upper()
        icon = self.ICON_MAP.get(key)
        display = f"{icon} {text}" if self._show_icon and icon else text
        self.setText(display)
        obj_name = self.STYLE_MAP.get(key, "badgeInfo")
        self.setObjectName(obj_name)
        # Force style refresh
        self.style().unpolish(self)
        self.style().polish(self)
