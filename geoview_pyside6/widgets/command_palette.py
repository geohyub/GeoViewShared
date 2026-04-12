"""
GeoView PySide6 -- Command Palette (Ctrl+K)
=============================================
VS Code / Linear 스타일 퍼지 검색 커맨드 팔레트.
Ctrl+K로 호출하여 모든 앱 액션에 빠르게 접근.

반투명 오버레이 위에 중앙 검색 박스가 뜨며,
타이핑하면 퍼지 매칭으로 액션을 필터링한다.
위/아래 화살표 선택, Enter 실행, Esc 닫기.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout, QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QSize, QEvent,
)
from PySide6.QtGui import QPainter, QColor, QFont

from geoview_pyside6.constants import Font, Space, Radius
from geoview_pyside6.theme_aware import c
from geoview_pyside6.effects import apply_shadow, anim_duration


# ── Category badge colors ──
_CATEGORY_COLORS: dict[str, str] = {
    "navigation": "#14b8a6",
    "project":    "#f59e0b",
    "settings":   "#3b82f6",
    "view":       "#a78bfa",
    "debug":      "#fbbf24",
    "file":       "#34d399",
    "edit":       "#fb7185",
}


def _badge_color(category: str) -> str:
    """Return badge background color for a category."""
    return _CATEGORY_COLORS.get(category.lower(), "#64748b")


@dataclass
class _Action:
    action_id: str
    label: str
    shortcut: str = ""
    category: str = ""
    icon_name: str = ""
    callback: Optional[Callable] = None


class CommandPalette(QWidget):
    """Ctrl+K command palette overlay.

    Full-screen translucent overlay with centered search box.
    Fuzzy-matches actions and executes on Enter/click.
    """

    action_triggered = Signal(str)

    # ── Geometry constants ──
    _BOX_WIDTH = 480
    _BOX_MAX_HEIGHT = 400
    _INPUT_HEIGHT = 44
    _ITEM_HEIGHT = 36
    _HEADER_HEIGHT = 26
    _MAX_VISIBLE_ITEMS = 10

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._actions: list[_Action] = []

        # Overlay covers entire parent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide()

        # Track parent resize to stay full-coverage
        if parent:
            parent.installEventFilter(self)

        # ── Central search container ──
        self._container = QWidget(self)
        self._container.setObjectName("cmdPaletteBox")

        box_layout = QVBoxLayout(self._container)
        box_layout.setContentsMargins(Space.SM, Space.SM, Space.SM, Space.SM)
        box_layout.setSpacing(2)

        # Search input
        self._search = QLineEdit()
        self._search.setPlaceholderText("  Type a command...")
        self._search.setFixedHeight(self._INPUT_HEIGHT)
        self._search.textChanged.connect(self._filter)
        self._search.installEventFilter(self)
        box_layout.addWidget(self._search)

        # Hint label (below input)
        self._hint = QLabel()
        self._hint.setObjectName("cmdPaletteHint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        box_layout.addWidget(self._hint)

        # Results list
        self._list = QListWidget()
        self._list.setObjectName("cmdPaletteList")
        self._list.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._list.itemActivated.connect(self._on_item_activated)
        self._list.itemClicked.connect(self._on_item_activated)
        box_layout.addWidget(self._list)

        # Shadow
        apply_shadow(self._container, level=3)

        # Apply styling
        self._apply_styles()

    # ══════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════

    def register_action(
        self,
        action_id: str,
        label: str,
        shortcut: str = "",
        category: str = "",
        icon_name: str = "",
        callback: Callable | None = None,
    ) -> None:
        """Register an action in the palette."""
        # Prevent duplicate IDs
        for existing in self._actions:
            if existing.action_id == action_id:
                return
        self._actions.append(_Action(
            action_id=action_id,
            label=label,
            shortcut=shortcut,
            category=category,
            icon_name=icon_name,
            callback=callback,
        ))

    def unregister_action(self, action_id: str) -> None:
        """Remove an action by ID."""
        self._actions = [a for a in self._actions if a.action_id != action_id]

    def clear_actions(self) -> None:
        """Remove all registered actions."""
        self._actions.clear()

    def show_palette(self) -> None:
        """Open the palette: reset search, show all actions, center box."""
        self._apply_styles()
        self._search.clear()
        self._populate(self._actions)
        self._update_hint(len(self._actions))

        # Cover full parent
        if self.parent():
            self.setGeometry(self.parent().rect())

        self.show()
        self.raise_()
        self._search.setFocus()

        # Fade-in
        dur = anim_duration(120)
        if dur > 0:
            opacity_fx = QGraphicsOpacityEffect(self._container)
            self._container.setGraphicsEffect(opacity_fx)
            anim = QPropertyAnimation(opacity_fx, b"opacity", self)
            anim.setDuration(dur)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(
                lambda: self._container.setGraphicsEffect(None)
            )
            anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            self._fade_anim = anim  # prevent GC

    def hide_palette(self) -> None:
        """Close the palette."""
        self.hide()

    # ══════════════════════════════════════════
    # Painting -- translucent backdrop
    # ══════════════════════════════════════════

    def paintEvent(self, event):
        """Draw the semi-transparent backdrop overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))  # rgba(0,0,0,0.4)
        painter.end()

    # ══════════════════════════════════════════
    # Events
    # ══════════════════════════════════════════

    def mousePressEvent(self, event):
        """Click on backdrop = close."""
        # Check if click is outside the container
        box_rect = self._container.geometry()
        if not box_rect.contains(event.pos()):
            self.hide_palette()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):
        """Esc close, Enter execute, arrows navigate."""
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.hide_palette()
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

    def eventFilter(self, obj, event):
        """Handle parent resize and search key forwarding."""
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            if self.isVisible():
                self.setGeometry(self.parent().rect())
        # Forward Up/Down/Enter/Escape from search input to palette
        if obj is self._search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (
                Qt.Key.Key_Down, Qt.Key.Key_Up,
                Qt.Key.Key_Return, Qt.Key.Key_Enter,
                Qt.Key.Key_Escape,
            ):
                self.keyPressEvent(event)
                return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        """Reposition the search box centered near top."""
        super().resizeEvent(event)
        self._position_container()

    def showEvent(self, event):
        """Position container on show."""
        super().showEvent(event)
        self._position_container()

    # ══════════════════════════════════════════
    # Internal -- layout
    # ══════════════════════════════════════════

    def _position_container(self) -> None:
        """Center the container horizontally, 20% from top."""
        w = self.width()
        h = self.height()
        box_w = self._BOX_WIDTH
        # Let height be natural (adjustSize)
        self._container.setFixedWidth(box_w)
        self._container.adjustSize()
        box_h = self._container.sizeHint().height()
        box_h = min(box_h, self._BOX_MAX_HEIGHT)
        self._container.setMaximumHeight(self._BOX_MAX_HEIGHT)
        x = (w - box_w) // 2
        y = max(int(h * 0.18), 40)
        self._container.move(x, y)

    # ══════════════════════════════════════════
    # Internal -- filtering
    # ══════════════════════════════════════════

    def _filter(self, text: str) -> None:
        """Fuzzy-match filter actions."""
        query = text.strip().lower()
        if not query:
            self._populate(self._actions)
            self._update_hint(len(self._actions))
            return

        scored: list[tuple[float, _Action]] = []
        for action in self._actions:
            # Match against label
            score = self._fuzzy_score(query, action.label.lower())
            # Also match against category
            cat_score = self._fuzzy_score(query, action.category.lower())
            if cat_score > score:
                score = cat_score
            # Substring match bonus
            if query in action.label.lower():
                score += 3.0
            if query in action.category.lower():
                score += 1.5
            if score > 0:
                scored.append((score, action))

        scored.sort(key=lambda x: -x[0])
        filtered = [a for _, a in scored]
        self._populate(filtered)
        self._update_hint(len(filtered))

    @staticmethod
    def _fuzzy_score(query: str, target: str) -> float:
        """All chars of query must appear in order in target. Returns score."""
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
                if ti == 0 or target[ti - 1] in (" ", "_", "-", "."):
                    score += 1.5
                last_match = ti
                qi += 1
        if qi < len(query):
            return 0.0
        return score

    # ══════════════════════════════════════════
    # Internal -- populate list
    # ══════════════════════════════════════════

    def _populate(self, actions: list[_Action]) -> None:
        """Fill the list widget with grouped actions."""
        self._list.clear()

        # Group by category
        categories: dict[str, list[_Action]] = {}
        for a in actions:
            cat = a.category or "General"
            categories.setdefault(cat, []).append(a)

        for cat_name, cat_actions in categories.items():
            # Category header (non-selectable)
            header_item = QListWidgetItem()
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_item.setSizeHint(QSize(0, self._HEADER_HEIGHT))
            self._list.addItem(header_item)

            header_widget = QLabel(cat_name.upper())
            header_widget.setObjectName("cmdPaletteCatHeader")
            header_widget.setStyleSheet(
                f"font-size: {Font.XS}px; "
                f"font-weight: {Font.MEDIUM}; "
                f"color: {c().DIM}; "
                f"letter-spacing: 1px; "
                f"padding: {Space.XS}px {Space.SM}px 0 {Space.SM}px; "
                f"background: transparent;"
            )
            self._list.setItemWidget(header_item, header_widget)

            # Action items
            for action in cat_actions:
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, action.action_id)
                item.setSizeHint(QSize(0, self._ITEM_HEIGHT))
                self._list.addItem(item)

                row = self._build_action_row(action)
                self._list.setItemWidget(item, row)

        # Adjust list height
        total = self._list.count()
        visible = min(total, self._MAX_VISIBLE_ITEMS + 2)
        estimated = visible * self._ITEM_HEIGHT
        self._list.setFixedHeight(min(estimated, 340))
        self._container.adjustSize()
        self._position_container()

    def _build_action_row(self, action: _Action) -> QWidget:
        """Build a single action row widget."""
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(Space.SM, 0, Space.SM, 0)
        layout.setSpacing(Space.SM)

        # Category badge (compact colored tag)
        if action.category:
            badge = QLabel(action.category[:3].upper())
            bg = _badge_color(action.category)
            badge.setStyleSheet(
                f"font-size: {Font.XS - 1}px; "
                f"font-weight: {Font.SEMIBOLD}; "
                f"color: #ffffff; "
                f"background: {bg}; "
                f"padding: 1px 5px; "
                f"border-radius: 3px; "
                f"letter-spacing: 0.5px;"
            )
            badge.setFixedHeight(18)
            layout.addWidget(badge)

        # Label
        label = QLabel(action.label)
        label.setStyleSheet(
            f"font-size: {Font.SM}px; "
            f"color: {c().TEXT}; "
            f"background: transparent;"
        )
        layout.addWidget(label)
        layout.addStretch()

        # Shortcut keycap badge (right side)
        if action.shortcut:
            for part in action.shortcut.split("+"):
                key_label = QLabel(part.strip())
                key_label.setStyleSheet(
                    f"font-size: {Font.XS - 1}px; "
                    f"font-weight: {Font.MEDIUM}; "
                    f"color: {c().MUTED}; "
                    f"background: {c().DARK}; "
                    f"padding: 2px 6px; "
                    f"border: 1px solid {c().BORDER}; "
                    f"border-radius: 3px; "
                    f"min-width: 16px;"
                )
                key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                key_label.setFixedHeight(20)
                layout.addWidget(key_label)

        return row

    # ══════════════════════════════════════════
    # Internal -- selection navigation
    # ══════════════════════════════════════════

    def _move_selection(self, delta: int) -> None:
        """Move selection, skipping non-selectable header items."""
        count = self._list.count()
        if count == 0:
            return
        current = self._list.currentRow()
        if current < 0:
            # Start from top or bottom
            target = 0 if delta > 0 else count - 1
        else:
            target = current + delta

        while 0 <= target < count:
            item = self._list.item(target)
            if item and item.data(Qt.ItemDataRole.UserRole):
                self._list.setCurrentRow(target)
                return
            target += delta

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        """Execute the selected action."""
        action_id = item.data(Qt.ItemDataRole.UserRole)
        if not action_id:
            return

        for action in self._actions:
            if action.action_id == action_id:
                if action.callback:
                    action.callback()
                self.action_triggered.emit(action_id)
                break

        self.hide_palette()

    # ══════════════════════════════════════════
    # Internal -- hint & styles
    # ══════════════════════════════════════════

    def _update_hint(self, count: int) -> None:
        """Update the hint text showing result count and key help."""
        self._hint.setText(
            f"{count} action{'s' if count != 1 else ''}  |  "
            f"Up/Down to navigate  |  Enter to run  |  Esc to close"
        )

    def _apply_styles(self) -> None:
        """Apply theme-aware styles to all sub-widgets."""
        colors = c()

        self._container.setStyleSheet(
            f"#cmdPaletteBox {{"
            f"  background: {colors.NAVY};"
            f"  border: 1px solid {colors.BORDER};"
            f"  border-radius: {Radius.LG}px;"
            f"}}"
        )

        self._search.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {colors.DARK};"
            f"  color: {colors.TEXT};"
            f"  border: 1px solid {colors.BORDER};"
            f"  border-radius: {Radius.SM}px;"
            f"  font-size: {Font.LG}px;"
            f"  padding: 0 {Space.MD}px;"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border-color: {colors.CYAN};"
            f"}}"
            f"QLineEdit::placeholder {{"
            f"  color: {colors.DIM};"
            f"}}"
        )

        self._hint.setStyleSheet(
            f"font-size: {Font.XS}px; "
            f"color: {colors.DIM}; "
            f"padding: 2px {Space.SM}px; "
            f"background: transparent;"
        )

        self._list.setStyleSheet(
            f"QListWidget {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  outline: none;"
            f"  padding-top: {Space.XS}px;"
            f"}}"
            f"QListWidget::item {{"
            f"  background: transparent;"
            f"  color: {colors.TEXT};"
            f"  border: none;"
            f"  border-radius: {Radius.SM}px;"
            f"  padding: 0; margin: 0;"
            f"}}"
            f"QListWidget::item:selected {{"
            f"  background: {colors.SLATE};"
            f"}}"
            f"QListWidget::item:hover {{"
            f"  background: {colors.DARK};"
            f"}}"
        )
