"""
Collapsible Section Widget
============================
접기/펼치기 가능한 섹션. QPropertyAnimation 으로 부드러운 전환.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QWidget, QSizePolicy,
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, Property,
)
from PySide6.QtGui import QCursor, QFont

from geoview_pyside6.constants import Dark, Font, Space, Radius
from geoview_pyside6.theme_aware import c


# Unicode triangles for chevron indicator
_CHEVRON_EXPANDED = "\u25BC"   # BLACK DOWN-POINTING TRIANGLE
_CHEVRON_COLLAPSED = "\u25B6"  # BLACK RIGHT-POINTING TRIANGLE

_ANIMATION_DURATION_MS = 200


class _ClickableHeader(QFrame):
    """내부 전용 -- 클릭 가능한 헤더 행."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class CollapsibleSection(QFrame):
    """
    접기/펼치기 가능한 섹션. 애니메이션 포함.

    Usage::

        section = CollapsibleSection("Options", expanded=False)
        section.set_content(my_form_widget)
        section.toggled.connect(lambda exp: print("expanded" if exp else "collapsed"))
    """

    toggled = Signal(bool)  # True = expanded

    def __init__(
        self,
        title: str,
        icon_name: str = "",
        expanded: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("collapsibleSection")
        self._expanded = expanded
        self._content_widget: QWidget | None = None
        self._animation: QPropertyAnimation | None = None
        self._target_height = 0

        # --- Main layout (vertical) ---
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # --- Header ---
        self._header = _ClickableHeader()
        self._header.setObjectName("collapsibleHeader")
        self._header.setFixedHeight(36)
        self._header.setStyleSheet(
            f"#collapsibleHeader {{"
            f"  background: {c().NAVY};"
            f"  border-bottom: 1px solid {c().BORDER};"
            f"  border-radius: 0px;"
            f"}}"
        )

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(Space.SM, 0, Space.SM, 0)
        header_layout.setSpacing(Space.SM)

        # Chevron
        self._chevron = QLabel()
        self._chevron.setFixedWidth(16)
        self._chevron.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chevron_font = QFont(Font.SANS, Font.XS)
        self._chevron.setFont(chevron_font)
        self._chevron.setStyleSheet(f"color: {c().MUTED}; background: transparent;")
        header_layout.addWidget(self._chevron)

        # Optional icon
        if icon_name:
            icon_label = QLabel(icon_name)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet(
                f"font-size: {Font.SM}px; color: {c().MUTED}; background: transparent;"
            )
            header_layout.addWidget(icon_label)

        # Title
        self._title_label = QLabel(title)
        title_font = QFont(Font.SANS, Font.SM)
        title_font.setWeight(QFont.Weight(Font.MEDIUM))
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet(
            f"color: {c().TEXT}; background: transparent;"
        )
        header_layout.addWidget(self._title_label)

        header_layout.addStretch()

        self._root_layout.addWidget(self._header)

        # --- Content container ---
        self._container = QFrame()
        self._container.setObjectName("collapsibleContent")
        self._container.setStyleSheet(
            f"#collapsibleContent {{ background: transparent; border: none; }}"
        )
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)

        self._root_layout.addWidget(self._container)

        # Initialise visual state (no animation on first draw)
        self._update_chevron()
        if not self._expanded:
            self._container.setMaximumHeight(0)

        # Connect click
        self._header.clicked.connect(self.toggle)

    # ── public API ───────────────────────────────────────

    def set_content(self, widget: QWidget) -> None:
        """콘텐츠 위젯 설정. 기존 콘텐츠가 있으면 교체."""
        if self._content_widget is not None:
            self._container_layout.removeWidget(self._content_widget)
            self._content_widget.setParent(None)

        self._content_widget = widget
        self._container_layout.addWidget(widget)

        # After content is set, refresh height bookkeeping
        widget.adjustSize()
        self._target_height = widget.sizeHint().height()

        if self._expanded:
            self._container.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX
        else:
            self._container.setMaximumHeight(0)

    def is_expanded(self) -> bool:
        return self._expanded

    def expand(self) -> None:
        if not self._expanded:
            self.toggle()

    def collapse(self) -> None:
        if self._expanded:
            self.toggle()

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._update_chevron()
        self._animate()
        self.toggled.emit(self._expanded)

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    # ── internals ────────────────────────────────────────

    def _update_chevron(self) -> None:
        self._chevron.setText(
            _CHEVRON_EXPANDED if self._expanded else _CHEVRON_COLLAPSED
        )

    def _animate(self) -> None:
        if self._content_widget is not None:
            self._target_height = self._content_widget.sizeHint().height()

        start = self._container.maximumHeight()
        end = self._target_height if self._expanded else 0

        # Clamp start value when expanding from 0
        if self._expanded and start == 0:
            start = 0
        # Clamp start value when collapsing from "unlimited"
        if not self._expanded and start > self._target_height:
            start = self._target_height

        if self._animation is not None:
            self._animation.stop()

        self._animation = QPropertyAnimation(self._container, b"maximumHeight")
        self._animation.setDuration(_ANIMATION_DURATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)

        # When expanding, remove the height cap after animation finishes so
        # the content can resize naturally.
        if self._expanded:
            self._animation.finished.connect(self._unlock_height)

        self._animation.start()

    def _unlock_height(self) -> None:
        if self._expanded:
            self._container.setMaximumHeight(16777215)
