"""
Dashboard Template Widget
===========================
KPI행 + 필터툴바 + 테이블 + 하단 슬롯의 표준 대시보드 레이아웃.
10+ 앱에서 반복되는 대시보드 구조를 단일 위젯으로 통합.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
)

from geoview_pyside6.constants import Space
from geoview_pyside6.effects import reveal_widget, stagger_reveal
from geoview_pyside6.surface_roles import harden_theme_surfaces


class DashboardTemplate(QWidget):
    """KPI행 + 필터툴바 + 테이블 + 하단 슬롯의 표준 대시보드 레이아웃.

    Usage::

        dashboard = DashboardTemplate()
        dashboard.add_kpi(kpi_pass).add_kpi(kpi_fail).add_kpi(kpi_total)
        dashboard.set_toolbar(my_filter_toolbar)
        dashboard.set_content(my_table_view)
        dashboard.set_footer(my_status_bar)

    Slots:
        1. KPI row    — QHBoxLayout, equal stretch per card
        2. Toolbar    — single widget slot (FilterToolbar or custom)
        3. Content    — flex stretch=1 (table or custom widget)
        4. Footer     — optional, max 160px height
    """

    _FOOTER_MAX_HEIGHT = 160

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        harden_theme_surfaces(self)
        self._revealed_once = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(Space.MD)

        # 1) KPI row
        self._kpi_row = QHBoxLayout()
        self._kpi_row.setContentsMargins(0, 0, 0, 0)
        self._kpi_row.setSpacing(Space.MD)
        root.addLayout(self._kpi_row)

        # 2) Toolbar slot
        self._toolbar_slot = QVBoxLayout()
        self._toolbar_slot.setContentsMargins(0, 0, 0, 0)
        self._toolbar_slot.setSpacing(0)
        root.addLayout(self._toolbar_slot)

        # 3) Content area (stretch=1)
        self._content_area = QVBoxLayout()
        self._content_area.setContentsMargins(0, 0, 0, 0)
        self._content_area.setSpacing(0)
        root.addLayout(self._content_area, 1)

        # 4) Footer slot
        self._footer_slot = QVBoxLayout()
        self._footer_slot.setContentsMargins(0, 0, 0, 0)
        self._footer_slot.setSpacing(0)
        root.addLayout(self._footer_slot)

        # Track current widgets for replacement
        self._toolbar_widget: QWidget | None = None
        self._content_widget: QWidget | None = None
        self._footer_widget: QWidget | None = None

    # ── KPI management ──────────────────────────────────

    def add_kpi(self, kpi_card: QWidget) -> DashboardTemplate:
        """KPI 카드 추가. 각 카드는 동일 stretch로 배치. 반환: self (체이닝)."""
        self._kpi_row.addWidget(kpi_card, 1)
        if self.isVisible():
            reveal_widget(kpi_card, offset_y=8, duration_ms=180)
        return self

    def kpi_row(self) -> QHBoxLayout:
        """KPI 행 레이아웃 직접 접근 (고급 커스터마이징용)."""
        return self._kpi_row

    # ── Slot setters ─────────────────────────────────────

    def set_toolbar(self, widget: QWidget) -> None:
        """툴바 슬롯에 위젯 설정. 기존 위젯이 있으면 교체."""
        self._replace_slot(self._toolbar_slot, self._toolbar_widget, widget)
        self._toolbar_widget = widget
        if self.isVisible():
            reveal_widget(widget, offset_y=10, duration_ms=180)

    def set_content(self, widget: QWidget) -> None:
        """콘텐츠 영역에 위젯 설정 (stretch=1). 기존 위젯이 있으면 교체."""
        self._replace_slot(self._content_area, self._content_widget, widget)
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )
        self._content_widget = widget
        if self.isVisible():
            reveal_widget(widget, offset_y=12, duration_ms=200)

    def set_footer(self, widget: QWidget) -> None:
        """푸터 슬롯에 위젯 설정. 최대 높이 160px 제한. 기존 위젯이 있으면 교체."""
        self._replace_slot(self._footer_slot, self._footer_widget, widget)
        widget.setMaximumHeight(self._FOOTER_MAX_HEIGHT)
        self._footer_widget = widget
        if self.isVisible():
            reveal_widget(widget, offset_y=10, duration_ms=180)

    # ── Slot getters ─────────────────────────────────────

    def toolbar_widget(self) -> QWidget | None:
        """현재 설정된 툴바 위젯."""
        return self._toolbar_widget

    def content_widget(self) -> QWidget | None:
        """현재 설정된 콘텐츠 위젯."""
        return self._content_widget

    def footer_widget(self) -> QWidget | None:
        """현재 설정된 푸터 위젯."""
        return self._footer_widget

    # ── Internal ─────────────────────────────────────────

    @staticmethod
    def _replace_slot(
        layout: QVBoxLayout,
        old_widget: QWidget | None,
        new_widget: QWidget,
    ) -> None:
        """레이아웃 슬롯의 위젯을 교체한다. 이전 위젯은 안전하게 제거."""
        if old_widget is not None:
            layout.removeWidget(old_widget)
            old_widget.setParent(None)  # type: ignore[arg-type]
        layout.addWidget(new_widget)

    def showEvent(self, event):
        super().showEvent(event)
        if self._revealed_once:
            return
        self._revealed_once = True

        kpis = [
            self._kpi_row.itemAt(i).widget()
            for i in range(self._kpi_row.count())
            if self._kpi_row.itemAt(i).widget() is not None
        ]
        stagger_reveal(kpis, offset_y=8, duration_ms=180, stagger_ms=40)

        for widget, offset, duration in (
            (self._toolbar_widget, 10, 180),
            (self._content_widget, 12, 220),
            (self._footer_widget, 10, 180),
        ):
            if widget is not None:
                reveal_widget(widget, offset_y=offset, duration_ms=duration)

    def refresh_theme(self) -> None:
        harden_theme_surfaces(self)
