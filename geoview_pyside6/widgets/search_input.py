"""
Search Input Widget
====================
Professional search input with icon prefix, rounded border, focus ring,
and clear button. All colors via c(), fonts via Font, spacing via Space.

Container: c().DARK bg, 1px border c().BORDER, 8px radius
Input: c().TEXT, 12px font, c().DIM placeholder
Search icon: left-aligned, c().DIM color
Focus: border changes to accent, focus ring
Clear button on hover (if text present)
"""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLineEdit, QLabel, QPushButton,
)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from geoview_pyside6.constants import Font, Radius, Space, rgba
from geoview_pyside6.theme_aware import c


class SearchInput(QFrame):
    """
    Search input with icon prefix, focus ring, clear button, and debounce.

    Usage:
        search = SearchInput(placeholder="Filter lines...")
        search.text_changed.connect(on_filter)
        search.cleared.connect(on_clear)
    """

    text_changed = Signal(str)  # debounced emit
    cleared = Signal()

    def __init__(
        self,
        placeholder: str = "Search...",
        debounce_ms: int = 300,
        width: int = 240,
        parent=None,
    ):
        super().__init__(parent)
        self._oid = f"searchInput_{id(self)}"
        self.setObjectName(self._oid)
        self.setFixedHeight(32)
        self.setFixedWidth(width)
        self._focused = False

        # --- Layout ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Space.SM, 0, Space.XS, 0)
        layout.setSpacing(Space.XS)

        # Search icon (magnifying glass)
        self._icon = QLabel("\u2315")  # search glyph
        self._icon.setFixedSize(20, 20)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet(
            f"color: {c().DIM};"
            f" font-size: {Font.SM}px;"
            f" background: transparent;"
            f" border: none;"
        )
        layout.addWidget(self._icon)

        # Line edit
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.setAccessibleName("Search input")
        self._edit.setStyleSheet(
            f"QLineEdit {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  color: {c().TEXT};"
            f"  font-size: {Font.SM}px;"
            f"  font-family: \"{Font.SANS}\";"
            f"  padding: 0;"
            f"  selection-background-color: {rgba(c().BLUE, 0.25)};"
            f"}}"
            f"QLineEdit::placeholder {{"
            f"  color: {c().DIM};"
            f"}}"
        )
        layout.addWidget(self._edit, 1)

        # Clear button (hidden when empty)
        self._clear_btn = QPushButton("\u2715")  # X
        self._clear_btn.setFixedSize(20, 20)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; border: none;"
            f"  color: {c().MUTED}; font-size: {Font.XS}px;"
            f"  border-radius: 10px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {c().SLATE}; color: {c().TEXT};"
            f"}}"
        )
        self._clear_btn.setVisible(False)
        self._clear_btn.clicked.connect(self.clear)
        layout.addWidget(self._clear_btn)

        # Apply base frame style
        self._apply_style()

        # --- Debounce timer ---
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(debounce_ms)
        self._debounce.timeout.connect(self._emit_text)

        # --- Connections ---
        self._edit.textChanged.connect(self._on_text_changed)

        # Track focus with event filter on the QLineEdit
        self._edit.installEventFilter(self)

    # ------------------------------------------------------------------
    # Focus ring via event filter
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        if obj is self._edit:
            if event.type() == QEvent.Type.FocusIn:
                self._focused = True
                self._apply_style()
            elif event.type() == QEvent.Type.FocusOut:
                self._focused = False
                self._apply_style()
        return super().eventFilter(obj, event)

    def _apply_style(self):
        if self._focused:
            border_color = c().CYAN
            # Simulated focus ring with a second brighter border
            self.setStyleSheet(
                f"QFrame#{self._oid} {{"
                f"  background: {c().DARK};"
                f"  border: 1px solid {border_color};"
                f"  border-radius: {Radius.BASE}px;"
                f"}}"
            )
            # Update icon color on focus
            self._icon.setStyleSheet(
                f"color: {c().CYAN};"
                f" font-size: {Font.SM}px;"
                f" background: transparent;"
                f" border: none;"
            )
        else:
            self.setStyleSheet(
                f"QFrame#{self._oid} {{"
                f"  background: {c().DARK};"
                f"  border: 1px solid {c().BORDER};"
                f"  border-radius: {Radius.BASE}px;"
                f"}}"
            )
            self._icon.setStyleSheet(
                f"color: {c().DIM};"
                f" font-size: {Font.SM}px;"
                f" background: transparent;"
                f" border: none;"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def text(self) -> str:
        """Return current input text."""
        return self._edit.text()

    def clear(self):
        """Clear input + emit cleared signal."""
        self._edit.clear()
        self._clear_btn.setVisible(False)
        self._debounce.stop()
        self.cleared.emit()
        self.text_changed.emit("")

    def set_placeholder(self, text: str):
        """Change placeholder text."""
        self._edit.setPlaceholderText(text)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_text_changed(self, text: str):
        """Called on each keystroke -- restart debounce + toggle clear button."""
        self._clear_btn.setVisible(bool(text))
        self._debounce.start()

    def _emit_text(self):
        """Called when debounce expires."""
        self.text_changed.emit(self._edit.text())

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def refresh_theme(self):
        """Re-apply all theme-dependent styles after a theme switch."""
        self._apply_style()
        self._edit.setStyleSheet(
            f"QLineEdit {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  color: {c().TEXT};"
            f"  font-size: {Font.SM}px;"
            f"  font-family: \"{Font.SANS}\";"
            f"  padding: 0;"
            f"  selection-background-color: {rgba(c().BLUE, 0.25)};"
            f"}}"
            f"QLineEdit::placeholder {{"
            f"  color: {c().DIM};"
            f"}}"
        )
        self._clear_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; border: none;"
            f"  color: {c().MUTED}; font-size: {Font.XS}px;"
            f"  border-radius: 10px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {c().SLATE}; color: {c().TEXT};"
            f"}}"
        )
