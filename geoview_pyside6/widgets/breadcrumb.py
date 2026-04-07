"""
GeoView PySide6 -- Breadcrumb Navigation
==========================================
Two breadcrumb widgets:

- ``Breadcrumb`` (legacy): push/pop stack for list -> detail -> edit flows.
- ``BreadcrumbBar`` (new): set_path() based bar for sidebar panel navigation.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal, Qt
from geoview_pyside6.constants import Font, Space, Radius
from geoview_pyside6.theme_aware import c


# ════════════════════════════════════════════
# BreadcrumbBar (new, set_path based)
# ════════════════════════════════════════════

class BreadcrumbBar(QFrame):
    """패널 탐색 경로를 보여주는 바.

    높이 28px, 투명 배경, 하단 테두리.
    ``set_path()`` 로 전체 경로를 한 번에 설정.
    항목 클릭 시 ``crumb_clicked`` 시그널 발신.

    Design:
    - 폰트: Font.XS
    - 구분자: ">" (c().DIM)
    - 현재 위치: c().TEXT_BRIGHT, 굵게
    - 이전 위치: c().MUTED, 호버 시 c().TEXT + 밑줄
    """

    crumb_clicked = Signal(str)  # panel_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setObjectName("breadcrumbBar")
        self._items: list[tuple[str, str]] = []  # [(panel_id, label), ...]

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(Space.LG, 0, Space.LG, 0)
        self._layout.setSpacing(Space.XS)
        self._layout.addStretch()

        self.refresh_theme()
        self.hide()  # 항목 없으면 숨김

    def set_path(self, items: list[tuple[str, str]]) -> None:
        """경로 전체 설정.

        Args:
            items: [(panel_id, label), ...] 형태. 마지막이 현재 위치.
        """
        self._items = list(items)
        self._rebuild()
        if self._items:
            self.show()
        else:
            self.hide()

    def refresh_theme(self) -> None:
        """테마 갱신."""
        self.setStyleSheet(
            f"#breadcrumbBar {{"
            f"  background: transparent;"
            f"  border-bottom: 1px solid {c().BORDER};"
            f"}}"
        )
        # 기존 항목이 있으면 재구성
        if self._items:
            self._rebuild()

    # ── Internal ──

    def _rebuild(self) -> None:
        """UI 재구성."""
        # 기존 위젯 정리 (stretch 제외)
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        colors = c()

        for i, (panel_id, label) in enumerate(self._items):
            is_last = (i == len(self._items) - 1)

            # 구분자 (첫 항목 제외)
            if i > 0:
                sep = QLabel("\u203a")  # single right-pointing angle
                sep.setStyleSheet(
                    f"color: {colors.DIM}; "
                    f"font-size: {Font.XS + 1}px; "
                    f"background: transparent; "
                    f"padding: 0 1px;"
                )
                self._layout.insertWidget(self._layout.count() - 1, sep)

            if is_last:
                # 현재 위치: 굵게, TEXT_BRIGHT
                lbl = QLabel(label)
                lbl.setStyleSheet(
                    f"color: {colors.TEXT_BRIGHT}; "
                    f"font-size: {Font.XS}px; "
                    f"font-weight: {Font.SEMIBOLD}; "
                    f"background: transparent;"
                )
                self._layout.insertWidget(self._layout.count() - 1, lbl)
            else:
                # 이전 위치: 클릭 가능
                btn = QPushButton(label)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f"  color: {colors.MUTED};"
                    f"  font-size: {Font.XS}px;"
                    f"  background: transparent;"
                    f"  border: none;"
                    f"  padding: 2px 4px;"
                    f"}}"
                    f"QPushButton:hover {{"
                    f"  color: {colors.TEXT};"
                    f"  text-decoration: underline;"
                    f"}}"
                )
                btn.clicked.connect(
                    lambda checked, pid=panel_id: self.crumb_clicked.emit(pid)
                )
                self._layout.insertWidget(self._layout.count() - 1, btn)


# ════════════════════════════════════════════
# Breadcrumb (legacy, push/pop stack)
# ════════════════════════════════════════════

class Breadcrumb(QFrame):
    """경로 기반 네비게이션 표시 (레거시). TopBar 아래에 배치."""
    navigated = Signal(str)  # crumb_id when clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setStyleSheet(
            f"Breadcrumb {{"
            f"  background: transparent;"
            f"  border-bottom: 1px solid {c().BORDER};"
            f"  padding: 0 {Space.LG}px;"
            f"}}"
        )
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(Space.LG, 0, Space.LG, 0)
        self._layout.setSpacing(Space.XS)
        self._crumbs: list[tuple[str, str]] = []  # (id, label)
        self._layout.addStretch()
        self.hide()  # Hidden when empty

    def push(self, crumb_id: str, label: str):
        """경로에 항목 추가."""
        self._crumbs.append((crumb_id, label))
        self._rebuild()
        self.show()

    def pop(self) -> str | None:
        """마지막 항목 제거. 제거된 id 반환."""
        if self._crumbs:
            cid, _ = self._crumbs.pop()
            self._rebuild()
            if not self._crumbs:
                self.hide()
            return cid
        return None

    def clear(self):
        """모든 경로 제거."""
        self._crumbs.clear()
        self._rebuild()
        self.hide()

    def _rebuild(self):
        """UI 재구성."""
        # Clear layout (except stretch at end)
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        colors = c()

        for i, (cid, label) in enumerate(self._crumbs):
            is_last = (i == len(self._crumbs) - 1)

            if i > 0:
                # Separator
                sep = QLabel(">")
                sep.setStyleSheet(
                    f"color: {colors.DIM}; "
                    f"font-size: {Font.XS}px; "
                    f"background: transparent;"
                )
                self._layout.insertWidget(self._layout.count() - 1, sep)

            if is_last:
                # Current page (not clickable)
                lbl = QLabel(label)
                lbl.setStyleSheet(
                    f"color: {colors.TEXT}; "
                    f"font-size: {Font.XS}px; "
                    f"font-weight: {Font.MEDIUM}; "
                    f"background: transparent;"
                )
                self._layout.insertWidget(self._layout.count() - 1, lbl)
            else:
                # Clickable breadcrumb
                btn = QPushButton(label)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(
                    f"QPushButton {{"
                    f"  color: {colors.MUTED};"
                    f"  font-size: {Font.XS}px;"
                    f"  background: transparent;"
                    f"  border: none;"
                    f"  padding: 2px 4px;"
                    f"}}"
                    f"QPushButton:hover {{"
                    f"  color: {colors.TEXT};"
                    f"  text-decoration: underline;"
                    f"}}"
                )
                btn.clicked.connect(
                    lambda checked, c_id=cid: self._on_crumb_clicked(c_id)
                )
                self._layout.insertWidget(self._layout.count() - 1, btn)

    def _on_crumb_clicked(self, crumb_id: str):
        # Remove all crumbs after this one
        idx = next(
            (i for i, (cid, _) in enumerate(self._crumbs) if cid == crumb_id),
            -1,
        )
        if idx >= 0:
            self._crumbs = self._crumbs[:idx + 1]
            self._rebuild()
        self.navigated.emit(crumb_id)
