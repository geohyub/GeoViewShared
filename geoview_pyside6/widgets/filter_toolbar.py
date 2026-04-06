"""
Filter Toolbar Widget
======================
필터 콤보 + 검색 + 액션 버튼 조합 툴바.
Builder-pattern 메서드 체이닝 지원.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QWidget, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from geoview_pyside6.constants import Dark, Font, Space, Radius
from geoview_pyside6.theme_aware import c

# Optional import: SearchInput (may not exist yet)
try:
    from geoview_pyside6.widgets.search_input import SearchInput as _SearchInput
except ImportError:
    _SearchInput = None


class FilterToolbar(QFrame):
    """
    필터 + 검색 + 액션 버튼 조합 툴바.

    Usage::

        toolbar = (
            FilterToolbar()
            .add_filter("status", "Status", ["All", "Pass", "Fail"], default="All")
            .add_filter("line", "Line", ["All", "L001", "L002"])
            .add_search("Search lines...")
            .add_stretch()
        )
        toolbar.add_action_button("Export", on_export, primary=True)
        toolbar.filters_changed.connect(on_filters_changed)
    """

    filters_changed = Signal(dict)  # {filter_name: selected_value, "_search": text}

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("filterToolbar")
        self.setFixedHeight(40)
        self.setStyleSheet(
            f"#filterToolbar {{ background: transparent; border: none; }}"
        )

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(Space.SM)

        self._combos: dict[str, QComboBox] = {}
        self._search_widget: QLineEdit | None = None
        self._debounce_timer: QTimer | None = None
        self._debounce_ms: int = 300

    # ── builder methods ──────────────────────────────────

    def add_filter(
        self,
        name: str,
        label: str,
        items: list[str],
        default: str = "",
    ) -> FilterToolbar:
        """콤보 필터 추가. 반환: self (체이닝)."""
        lbl = QLabel(label)
        lbl_font = QFont(Font.SANS, Font.XS)
        lbl.setFont(lbl_font)
        lbl.setStyleSheet(f"color: {c().DIM}; background: transparent;")
        self._layout.addWidget(lbl)

        combo = QComboBox()
        combo.setObjectName(f"filterCombo_{name}")
        combo.addItems(items)
        combo.setFixedWidth(120)
        combo.setStyleSheet(self._combo_qss())

        if default and default in items:
            combo.setCurrentText(default)

        combo.currentTextChanged.connect(lambda _val: self._emit_filters())
        self._combos[name] = combo
        self._layout.addWidget(combo)

        return self

    def add_search(
        self,
        placeholder: str = "Search...",
        debounce_ms: int = 300,
    ) -> FilterToolbar:
        """검색 입력 추가. 반환: self (체이닝)."""
        self._debounce_ms = debounce_ms

        if _SearchInput is not None:
            # SearchInput has its own debounce and emits text_changed(str)
            widget = _SearchInput(
                placeholder=placeholder, debounce_ms=debounce_ms,
            )
            self._search_widget = widget
            self._search_widget.setFixedHeight(28)
            self._search_widget.setMinimumWidth(160)
            self._search_widget.setMaximumWidth(260)
            # Connect SearchInput's debounced signal directly
            widget.text_changed.connect(lambda _t: self._emit_filters())
        else:
            # Fallback: plain QLineEdit with manual debounce
            widget = QLineEdit()
            widget.setPlaceholderText(placeholder)
            widget.setClearButtonEnabled(True)
            widget.setStyleSheet(self._search_qss())
            self._search_widget = widget
            self._search_widget.setFixedHeight(28)
            self._search_widget.setMinimumWidth(160)
            self._search_widget.setMaximumWidth(260)
            # Manual debounce
            self._debounce_timer = QTimer(self)
            self._debounce_timer.setSingleShot(True)
            self._debounce_timer.timeout.connect(self._emit_filters)
            widget.textChanged.connect(self._on_search_text_changed)

        self._layout.addWidget(self._search_widget)
        return self

    def add_action_button(
        self,
        text: str,
        callback,
        primary: bool = False,
        icon_name: str = "",
    ) -> QPushButton:
        """액션 버튼 추가. 반환: QPushButton (체이닝 아님)."""
        btn = QPushButton(f"{icon_name}  {text}".strip() if icon_name else text)
        btn.setObjectName("primaryButton" if primary else "secondaryButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(28)
        btn.setStyleSheet(
            self._btn_primary_qss() if primary else self._btn_secondary_qss()
        )
        btn.clicked.connect(callback)
        self._layout.addWidget(btn)
        return btn

    def add_stretch(self) -> FilterToolbar:
        """남은 공간 채우기. 반환: self (체이닝)."""
        self._layout.addStretch()
        return self

    # ── getters ───────────────────────────────────────────

    def get_filters(self) -> dict[str, str]:
        """현재 콤보 필터 값 딕셔너리."""
        return {name: combo.currentText() for name, combo in self._combos.items()}

    def get_search_text(self) -> str:
        """현재 검색 텍스트."""
        if self._search_widget is not None:
            return self._search_widget.text()
        return ""

    def reset(self) -> None:
        """모든 필터를 초기 상태(첫번째 항목)로, 검색 텍스트를 비움."""
        for combo in self._combos.values():
            combo.setCurrentIndex(0)
        if self._search_widget is not None:
            self._search_widget.clear()

    # ── internals ────────────────────────────────────────

    def _on_search_text_changed(self, _text: str) -> None:
        if self._debounce_timer is not None:
            self._debounce_timer.start(self._debounce_ms)

    def _emit_filters(self) -> None:
        result = self.get_filters()
        result["_search"] = self.get_search_text()
        self.filters_changed.emit(result)

    # ── QSS helpers ──────────────────────────────────────

    @staticmethod
    def _combo_qss() -> str:
        return (
            f"QComboBox {{"
            f"  background: {c().DARK};"
            f"  color: {c().TEXT};"
            f"  border: 1px solid {c().BORDER};"
            f"  border-radius: {Radius.SM}px;"
            f"  padding: 2px 8px;"
            f"  font-size: {Font.XS}px;"
            f"  min-height: 22px;"
            f"}}"
            f"QComboBox:hover {{"
            f"  border-color: {c().BORDER_H};"
            f"}}"
            f"QComboBox::drop-down {{"
            f"  border: none;"
            f"  width: 20px;"
            f"}}"
            f"QComboBox QAbstractItemView {{"
            f"  background: {c().NAVY};"
            f"  color: {c().TEXT};"
            f"  selection-background-color: {c().SLATE};"
            f"  border: 1px solid {c().BORDER};"
            f"  font-size: {Font.XS}px;"
            f"}}"
        )

    @staticmethod
    def _search_qss() -> str:
        return (
            f"QLineEdit {{"
            f"  background: {c().DARK};"
            f"  color: {c().TEXT};"
            f"  border: 1px solid {c().BORDER};"
            f"  border-radius: {Radius.SM}px;"
            f"  padding: 2px 8px;"
            f"  font-size: {Font.XS}px;"
            f"  selection-background-color: {c().SLATE};"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border-color: {c().BLUE};"
            f"}}"
            f"QLineEdit::placeholder {{"
            f"  color: {c().DIM};"
            f"}}"
        )

    @staticmethod
    def _btn_primary_qss() -> str:
        return (
            f"QPushButton#primaryButton {{"
            f"  background: {c().GREEN};"
            f"  color: {c().BG};"
            f"  border: none;"
            f"  border-radius: {Radius.SM}px;"
            f"  font-size: {Font.XS}px;"
            f"  font-weight: {Font.SEMIBOLD};"
            f"  padding: 4px 14px;"
            f"}}"
            f"QPushButton#primaryButton:hover {{"
            f"  background: {c().GREEN_H};"
            f"}}"
            f"QPushButton#primaryButton:disabled {{"
            f"  background: {c().SLATE};"
            f"  color: {c().DIM};"
            f"}}"
        )

    @staticmethod
    def _btn_secondary_qss() -> str:
        return (
            f"QPushButton#secondaryButton {{"
            f"  background: transparent;"
            f"  color: {c().MUTED};"
            f"  border: 1px solid {c().BORDER};"
            f"  border-radius: {Radius.SM}px;"
            f"  font-size: {Font.XS}px;"
            f"  padding: 4px 14px;"
            f"}}"
            f"QPushButton#secondaryButton:hover {{"
            f"  background: {c().DARK};"
            f"  color: {c().TEXT};"
            f"  border-color: {c().BORDER_H};"
            f"}}"
        )
