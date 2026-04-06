"""
GeoView PySide6 — Breadcrumb Navigation
==========================================
목록 → 상세 → 편집 흐름에서 경로 표시 + 뒤로가기.
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal, Qt
from geoview_pyside6.constants import Dark, Font, Space, Radius
from geoview_pyside6.theme_aware import c


class Breadcrumb(QFrame):
    """경로 기반 네비게이션 표시. TopBar 아래에 배치."""
    navigated = Signal(str)  # crumb_id when clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setStyleSheet(f"""
            Breadcrumb {{
                background: transparent;
                border-bottom: 1px solid {c().BORDER};
                padding: 0 {Space.LG}px;
            }}
        """)
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

        for i, (cid, label) in enumerate(self._crumbs):
            is_last = (i == len(self._crumbs) - 1)

            if i > 0:
                # Separator
                sep = QLabel(">")  # or chevron-right
                sep.setStyleSheet(f"color: {c().DIM}; font-size: {Font.XS}px; background: transparent;")
                self._layout.insertWidget(self._layout.count() - 1, sep)

            if is_last:
                # Current page (not clickable)
                lbl = QLabel(label)
                lbl.setStyleSheet(f"color: {c().TEXT}; font-size: {Font.XS}px; font-weight: {Font.MEDIUM}; background: transparent;")
                self._layout.insertWidget(self._layout.count() - 1, lbl)
            else:
                # Clickable breadcrumb
                btn = QPushButton(label)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {c().MUTED};
                        font-size: {Font.XS}px;
                        background: transparent;
                        border: none;
                        padding: 2px 4px;
                    }}
                    QPushButton:hover {{
                        color: {c().TEXT};
                        text-decoration: underline;
                    }}
                """)
                btn.clicked.connect(lambda checked, c=cid: self._on_crumb_clicked(c))
                self._layout.insertWidget(self._layout.count() - 1, btn)

    def _on_crumb_clicked(self, crumb_id: str):
        # Remove all crumbs after this one
        idx = next((i for i, (cid, _) in enumerate(self._crumbs) if cid == crumb_id), -1)
        if idx >= 0:
            self._crumbs = self._crumbs[:idx + 1]
            self._rebuild()
        self.navigated.emit(crumb_id)
