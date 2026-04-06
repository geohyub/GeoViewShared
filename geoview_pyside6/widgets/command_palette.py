"""
GeoView PySide6 — Command Palette
====================================
VS Code 스타일 퍼지 검색 커맨드 팔레트.
Ctrl+Shift+P로 호출하여 모든 앱 액션에 빠르게 접근.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout, QWidget, QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QFont

from geoview_pyside6.constants import Dark, Font, Space, Radius
from geoview_pyside6.theme_aware import c
from geoview_pyside6.effects import apply_shadow


@dataclass
class _Action:
    action_id: str
    label: str
    shortcut: str = ""
    category: str = ""
    icon_name: str = ""
    callback: Optional[Callable] = None


class CommandPalette(QDialog):
    """퍼지 검색 커맨드 팔레트 -- Ctrl+Shift+P로 호출."""

    action_triggered = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._actions: list[_Action] = []

        # Frameless popup
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(500)
        self.setMaximumHeight(400)

        # Container for rounded background
        self._container = QWidget(self)
        self._container.setObjectName("cmdPaletteContainer")
        self._container.setStyleSheet(f"""
            #cmdPaletteContainer {{
                background: {c().NAVY};
                border: 1px solid {c().BORDER};
                border-radius: {Radius.BASE}px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(Space.SM, Space.SM, Space.SM, Space.SM)
        layout.setSpacing(0)

        # Search input
        self._search = QLineEdit()
        self._search.setPlaceholderText("  Type a command...")
        self._search.setFixedHeight(40)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {c().DARK};
                color: {c().TEXT};
                border: none;
                border-radius: {Radius.SM}px;
                font-size: {Font.BASE}px;
                padding: 0 {Space.MD}px;
            }}
            QLineEdit::placeholder {{
                color: {c().DIM};
            }}
        """)
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        # Results list
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
                padding-top: {Space.XS}px;
            }}
            QListWidget::item {{
                background: transparent;
                color: {c().TEXT};
                border: none;
                border-radius: {Radius.SM}px;
                padding: 0;
                margin: 0;
            }}
            QListWidget::item:selected {{
                background: {c().SLATE};
            }}
            QListWidget::item:hover {{
                background: {c().DARK};
            }}
        """)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.itemActivated.connect(self._on_item_activated)
        self._list.itemClicked.connect(self._on_item_activated)
        layout.addWidget(self._list)

        # Drop shadow
        apply_shadow(self._container, level=3)

    # ── Public API ──

    def register_action(
        self,
        action_id: str,
        label: str,
        shortcut: str = "",
        category: str = "",
        icon_name: str = "",
        callback: Callable | None = None,
    ) -> None:
        """액션 등록."""
        self._actions.append(_Action(
            action_id=action_id,
            label=label,
            shortcut=shortcut,
            category=category,
            icon_name=icon_name,
            callback=callback,
        ))

    def show_palette(self) -> None:
        """팔레트 열기 -- 검색 초기화, 전체 액션 표시, 부모 중앙 배치."""
        self._search.clear()
        self._populate(self._actions)

        # Center on parent
        if self.parent():
            parent = self.parent()
            pw = parent.width()
            ph = parent.height()
            pg = parent.mapToGlobal(parent.rect().topLeft())
            x = pg.x() + (pw - self.width()) // 2
            y = pg.y() + int(ph * 0.2)  # 20% from top
            self.move(x, y)

        self.show()
        self._search.setFocus()

        # Fade-in animation
        opacity = QGraphicsOpacityEffect(self._container)
        self._container.setGraphicsEffect(opacity)
        anim = QPropertyAnimation(opacity, b"opacity", self)
        anim.setDuration(100)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: self._container.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._fade_anim = anim  # prevent GC

    # ── Internal ──

    def _filter(self, text: str) -> None:
        """퍼지 매치 필터링."""
        query = text.strip().lower()
        if not query:
            self._populate(self._actions)
            return

        scored: list[tuple[float, _Action]] = []
        for action in self._actions:
            score = self._fuzzy_score(query, action.label.lower())
            if score > 0:
                # Boost by category match
                if query in action.category.lower():
                    score += 0.5
                scored.append((score, action))

        scored.sort(key=lambda x: -x[0])
        self._populate([a for _, a in scored])

    @staticmethod
    def _fuzzy_score(query: str, target: str) -> float:
        """Check if all chars of query appear in order in target. Return score."""
        qi = 0
        score = 0.0
        last_match = -1
        for ti, ch in enumerate(target):
            if qi < len(query) and ch == query[qi]:
                # Consecutive match bonus
                if ti == last_match + 1:
                    score += 2.0
                else:
                    score += 1.0
                # Start-of-word bonus
                if ti == 0 or target[ti - 1] in (' ', '_', '-', '.'):
                    score += 1.5
                last_match = ti
                qi += 1
        if qi < len(query):
            return 0.0  # not all chars matched
        return score

    def _populate(self, actions: list[_Action]) -> None:
        """리스트 위젯에 액션 채우기 (카테고리 그룹)."""
        self._list.clear()

        # Group by category
        categories: dict[str, list[_Action]] = {}
        for a in actions:
            cat = a.category or "General"
            categories.setdefault(cat, []).append(a)

        for cat_name, cat_actions in categories.items():
            # Category header
            header_item = QListWidgetItem()
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)  # non-selectable
            header_item.setSizeHint(QSize(0, 24))
            self._list.addItem(header_item)

            header_widget = QLabel(cat_name.upper())
            header_widget.setStyleSheet(f"""
                font-size: {Font.XS}px;
                font-weight: {Font.MEDIUM};
                color: {c().DIM};
                letter-spacing: 1px;
                padding: {Space.XS}px {Space.SM}px 0 {Space.SM}px;
                background: transparent;
            """)
            self._list.setItemWidget(header_item, header_widget)

            # Action items
            for action in cat_actions:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, action.action_id)
                item.setSizeHint(QSize(0, 36))
                self._list.addItem(item)

                row_widget = QWidget()
                row_widget.setStyleSheet("background: transparent;")
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(Space.SM, 0, Space.SM, 0)
                row_layout.setSpacing(Space.SM)

                # Label
                label = QLabel(action.label)
                label.setStyleSheet(f"""
                    font-size: {Font.SM}px;
                    color: {c().TEXT};
                    background: transparent;
                """)
                row_layout.addWidget(label)

                row_layout.addStretch()

                # Shortcut (right-aligned)
                if action.shortcut:
                    shortcut_label = QLabel(action.shortcut)
                    shortcut_label.setStyleSheet(f"""
                        font-size: {Font.XS}px;
                        color: {c().DIM};
                        background: transparent;
                        padding: 2px 6px;
                        border: 1px solid {c().BORDER};
                        border-radius: 3px;
                    """)
                    row_layout.addWidget(shortcut_label)

                self._list.setItemWidget(item, row_widget)

        # Adjust dialog height
        total = self._list.count()
        row_height = 36
        header_height = 24
        # Estimate: rough height based on items (max 10 visible)
        visible_items = min(total, 12)
        list_height = visible_items * row_height
        self._list.setFixedHeight(min(list_height, 360))
        self.adjustSize()

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        """선택된 액션 실행."""
        action_id = item.data(Qt.ItemDataRole.UserRole)
        if not action_id:
            return  # header item

        # Find action and execute callback
        for action in self._actions:
            if action.action_id == action_id:
                if action.callback:
                    action.callback()
                self.action_triggered.emit(action_id)
                break

        self.close()

    def keyPressEvent(self, event):
        """Escape로 닫기, Enter로 선택, 화살표로 네비게이션."""
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            current = self._list.currentItem()
            if current and current.data(Qt.ItemDataRole.UserRole):
                self._on_item_activated(current)
        elif key == Qt.Key.Key_Down:
            self._move_selection(1)
        elif key == Qt.Key.Key_Up:
            self._move_selection(-1)
        else:
            super().keyPressEvent(event)

    def _move_selection(self, delta: int) -> None:
        """선택 항목 이동 (카테고리 헤더 건너뛰기)."""
        count = self._list.count()
        if count == 0:
            return
        current = self._list.currentRow()
        target = current + delta

        # Skip non-selectable header items
        while 0 <= target < count:
            item = self._list.item(target)
            if item and item.data(Qt.ItemDataRole.UserRole):
                self._list.setCurrentRow(target)
                return
            target += delta
