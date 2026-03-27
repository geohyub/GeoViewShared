"""
KPI Card Widget
================
큰 숫자 + 라벨 + 선택적 트렌드 표시.
숫자는 Geist Mono tabular-nums로 표시.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from geoview_pyside6.constants import Font, Space, Dark


class KPICard(QFrame):
    """
    KPI 카드 위젯.

    Usage:
        card = KPICard("📊", "1,231", "Total Tests", trend="+12%")
    """

    def __init__(
        self,
        icon: str = "📊",
        value: str = "—",
        label: str = "",
        trend: str = "",
        accent: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.setObjectName("gvCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Space.BASE, Space.MD, Space.BASE, Space.MD)
        layout.setSpacing(Space.SM)

        # Icon (hidden when empty)
        if icon:
            icon_label = QLabel(icon)
            icon_label.setFixedSize(44, 44)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet(
                f"font-size: 20px; background: {accent or Dark.BLUE}1A; "
                f"border-radius: 8px;"
            )
            layout.addWidget(icon_label)

        # Value + Label
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        # Value row (value + optional trend)
        value_row = QHBoxLayout()
        value_row.setSpacing(Space.SM)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("kpiValue")
        value_row.addWidget(self._value_label)

        if trend:
            self._trend_label = QLabel(trend)
            if trend.startswith("+"):
                self._trend_label.setObjectName("badgePass")
            elif trend.startswith("-"):
                self._trend_label.setObjectName("badgeFail")
            else:
                self._trend_label.setObjectName("badgeInfo")
            value_row.addWidget(self._trend_label)

        value_row.addStretch()
        text_layout.addLayout(value_row)

        self._label = QLabel(label)
        self._label.setObjectName("kpiLabel")
        text_layout.addWidget(self._label)

        layout.addLayout(text_layout)
        layout.addStretch()

    def set_value(self, value: str):
        self._value_label.setText(value)

    def set_label(self, label: str):
        self._label.setText(label)
