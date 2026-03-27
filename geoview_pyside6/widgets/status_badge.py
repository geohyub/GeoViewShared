"""
Status Badge Widget
====================
PASS/WARN/FAIL/INFO 상태를 색상 배지로 표시.
"""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class StatusBadge(QLabel):
    """
    상태 배지.

    Usage:
        badge = StatusBadge("PASS")
        badge = StatusBadge("FAIL")
        badge = StatusBadge("A", badge_type="grade")
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

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_status(text)

    def update_status(self, text: str):
        self.setText(text)
        obj_name = self.STYLE_MAP.get(text.upper(), "badgeInfo")
        self.setObjectName(obj_name)
        # Force style refresh
        self.style().unpolish(self)
        self.style().polish(self)
