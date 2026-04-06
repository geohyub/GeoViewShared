"""
Form Field Widget
==================
폼 필드 -- 라벨 + 입력 + 에러 메시지 + 힌트 텍스트.
text / combo / textarea 타입 지원.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QTextEdit, QWidget,
)
from PySide6.QtCore import Qt, Signal, QTimer
from geoview_pyside6.constants import Font, Radius, Space, rgba
from geoview_pyside6.theme_aware import c


class FormField(QFrame):
    """
    폼 필드 -- 라벨 + 입력 + 에러 메시지 + 힌트 텍스트.

    Usage:
        name = FormField("Name", required=True, placeholder="Enter name")
        kind = FormField("Type", field_type="combo", items=["A", "B", "C"])
        desc = FormField("Description", field_type="textarea", hint="Optional notes")

        name.value_changed.connect(on_change)
        if name.validate():
            print(name.value())
    """

    value_changed = Signal(str)

    _INPUT_HEIGHT = 34
    _TEXTAREA_HEIGHT = 80

    def __init__(
        self,
        label: str,
        field_type: str = "text",
        placeholder: str = "",
        hint: str = "",
        required: bool = False,
        items: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._required = required
        self._field_type = field_type
        self._label_text = label

        self.setStyleSheet("QFrame { background: transparent; border: none; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(Space.XS)

        # ── Label row ────────────────────────────────────────────────
        label_row = QHBoxLayout()
        label_row.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {c().TEXT}; font-size: {Font.SM}px; "
            f"font-weight: {Font.MEDIUM}; background: transparent; border: none;"
        )
        label_row.addWidget(lbl)

        if required:
            asterisk = QLabel("*")
            asterisk.setStyleSheet(
                f"color: {c().RED}; font-size: {Font.SM}px; "
                f"font-weight: {Font.BOLD}; background: transparent; border: none;"
            )
            label_row.addWidget(asterisk)

        label_row.addStretch()
        root.addLayout(label_row)

        # ── Input widget ─────────────────────────────────────────────
        self._input: QLineEdit | QComboBox | QTextEdit

        base_style = (
            f"background: {c().DARK};"
            f"color: {c().TEXT};"
            f"border: 1px solid {c().BORDER};"
            f"border-radius: {Radius.SM}px;"
            f"font-size: {Font.SM}px;"
            f"padding: 4px {Space.SM}px;"
            f"selection-background-color: {rgba(c().BLUE, 0.25)};"
        )

        if field_type == "combo":
            self._input = QComboBox()
            if items:
                self._input.addItems(items)
            self._input.setFixedHeight(self._INPUT_HEIGHT)
            self._input.setStyleSheet(
                f"QComboBox {{ {base_style} }}"
                f"QComboBox::drop-down {{"
                f"  border: none; width: 24px;"
                f"}}"
                f"QComboBox::down-arrow {{"
                f"  image: none; border: none;"
                f"}}"
                f"QComboBox QAbstractItemView {{"
                f"  background: {c().NAVY};"
                f"  color: {c().TEXT};"
                f"  border: 1px solid {c().BORDER};"
                f"  selection-background-color: {c().SLATE};"
                f"  font-size: {Font.SM}px;"
                f"}}"
            )
            self._input.currentTextChanged.connect(self._on_value_changed)

        elif field_type == "textarea":
            self._input = QTextEdit()
            self._input.setFixedHeight(self._TEXTAREA_HEIGHT)
            self._input.setPlaceholderText(placeholder)
            self._input.setStyleSheet(f"QTextEdit {{ {base_style} }}")
            self._input.textChanged.connect(
                lambda: self._on_value_changed(self._input.toPlainText())
            )

        else:  # "text" (default)
            self._input = QLineEdit()
            self._input.setFixedHeight(self._INPUT_HEIGHT)
            self._input.setPlaceholderText(placeholder)
            self._input.setStyleSheet(
                f"QLineEdit {{ {base_style} }}"
                f"QLineEdit::placeholder {{ color: {c().DIM}; }}"
            )
            self._input.textChanged.connect(self._on_value_changed)

        root.addWidget(self._input)

        # Accessibility
        self._input.setAccessibleName(label)

        # ── Live validation timer (debounced) ────────────────────────
        self._validate_timer = QTimer(self)
        self._validate_timer.setSingleShot(True)
        self._validate_timer.setInterval(500)
        self._validate_timer.timeout.connect(self._live_validate)

        if isinstance(self._input, QLineEdit):
            self._input.textChanged.connect(lambda: self._validate_timer.start())

        # ── Error label (hidden by default) ──────────────────────────
        self._error_label = QLabel()
        self._error_label.setStyleSheet(
            f"color: {c().RED}; font-size: {Font.XS}px; "
            "background: transparent; border: none;"
        )
        self._error_label.setVisible(False)
        self._error_label.setWordWrap(True)
        root.addWidget(self._error_label)

        # ── Hint label (always visible if provided) ──────────────────
        self._hint_label = QLabel()
        self._hint_label.setStyleSheet(
            f"color: {c().DIM}; font-size: {Font.XS}px; "
            "background: transparent; border: none;"
        )
        self._hint_label.setWordWrap(True)
        if hint:
            self._hint_label.setText(hint)
            self._hint_label.setVisible(True)
        else:
            self._hint_label.setVisible(False)
        root.addWidget(self._hint_label)

        # Cache normal border style for error reset
        self._normal_border = f"1px solid {c().BORDER}"
        self._error_border = f"1px solid {c().RED}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def value(self) -> str:
        """현재 값 반환."""
        if isinstance(self._input, QComboBox):
            return self._input.currentText()
        if isinstance(self._input, QTextEdit):
            return self._input.toPlainText()
        return self._input.text()

    def set_value(self, val: str):
        """값 설정."""
        if isinstance(self._input, QComboBox):
            idx = self._input.findText(val)
            if idx >= 0:
                self._input.setCurrentIndex(idx)
        elif isinstance(self._input, QTextEdit):
            self._input.setPlainText(val)
        else:
            self._input.setText(val)

    def set_error(self, msg: str):
        """에러 메시지 표시 + 입력 테두리 빨간색."""
        self._error_label.setText(msg)
        self._error_label.setVisible(True)
        self._apply_border(self._error_border)

    def clear_error(self):
        """에러 메시지 숨기기 + 테두리 복원."""
        self._error_label.setText("")
        self._error_label.setVisible(False)
        self._apply_border(self._normal_border)

    def set_enabled(self, enabled: bool):
        """활성/비활성 전환."""
        self._input.setEnabled(enabled)
        opacity = "FF" if enabled else "60"
        self._input.setStyleSheet(
            self._input.styleSheet().replace(
                f"color: {c().TEXT}",
                f"color: {c().TEXT}{opacity}",
            )
        )

    def validate(self) -> bool:
        """필수 필드 검증. 빈 값이면 에러 표시 후 False 반환."""
        if self._required and not self.value().strip():
            self.set_error("This field is required.")
            return False
        self.clear_error()
        return True

    def field_widget(self) -> QWidget:
        """내부 입력 위젯(QLineEdit / QComboBox / QTextEdit) 직접 접근."""
        return self._input

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_value_changed(self, text: str):
        """값 변경 시 에러 자동 해제 + 시그널 emit."""
        if self._error_label.isVisible():
            self.clear_error()
        self.value_changed.emit(text)

    def _live_validate(self):
        """실시간 유효성 검사 (디바운스 후)."""
        if self._required and not self.value().strip():
            # Don't show error for empty required fields while typing
            # Only show after explicit validate() call
            return
        # Clear any previous error if now valid
        if self.value().strip():
            self.clear_error()

    def _apply_border(self, border: str):
        """입력 위젯의 border 스타일만 교체."""
        old_ss = self._input.styleSheet()
        # Replace border declaration
        import re
        new_ss = re.sub(
            r"border:\s*[^;]+;",
            f"border: {border};",
            old_ss,
            count=1,
        )
        self._input.setStyleSheet(new_ss)


class FormFieldGroup(QFrame):
    """여러 FormField를 묶어 Tab 순서를 자동 설정하고 일괄 검증."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(Space.MD)
        self._fields: list[FormField] = []

    def add_field(self, field: FormField) -> FormField:
        """필드 추가. 자동 Tab 순서 설정."""
        self._layout.addWidget(field)
        if self._fields:
            # Set tab order: previous field's input -> this field's input
            prev_widget = self._fields[-1].field_widget()
            curr_widget = field.field_widget()
            if prev_widget and curr_widget:
                QWidget.setTabOrder(prev_widget, curr_widget)
        self._fields.append(field)
        return field

    def validate_all(self) -> bool:
        """모든 필드 검증. 첫 실패 필드에 포커스. 반환: 전체 유효 여부."""
        all_valid = True
        first_invalid = None
        for field in self._fields:
            if not field.validate():
                all_valid = False
                if first_invalid is None:
                    first_invalid = field
        if first_invalid:
            w = first_invalid.field_widget()
            if w:
                w.setFocus()
        return all_valid

    def values(self) -> dict[str, str]:
        """모든 필드의 {label: value} 딕셔너리 반환."""
        return {f._label_text: f.value() for f in self._fields}

    def clear_all(self):
        """모든 필드 초기화."""
        for f in self._fields:
            f.set_value("")
            f.clear_error()

    def fields(self) -> list[FormField]:
        return list(self._fields)
