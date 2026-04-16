"""
N2 ShortcutHintBanner — hover 시 단축키 힌트 상단 배너 (Wave 6 Week 22 Day 3)

참조: plans/new_widgets_spec.md §1
시나리오 1·3 의 "단축키 모름" 통증 대응.

Depends on (read-only, Day 3 tip):
    (none — pure PySide6)
effects.py / animated_stack.py 결합 0. 단순 show/hide 로 구현.
애니메이션 (fade-in 200 ms) 는 Day 4 pyqtgraph 전환 이후 선택적 확장 예정.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class ShortcutHintBanner(QFrame):
    """전역 hover 힌트 배너 (단일 인스턴스, MainWindow 당 1 개)."""

    _PROPERTY_SHORTCUT = "_shortcut_hint_keys"
    _PROPERTY_MESSAGE = "_shortcut_hint_text"
    _HOVER_DELAY_MS = 600
    _HEIGHT_PX = 28

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ShortcutHintBanner")
        self.setFixedHeight(self._HEIGHT_PX)
        self._enabled = True
        self._pending_widget: QWidget | None = None
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.setInterval(self._HOVER_DELAY_MS)
        self._delay_timer.timeout.connect(self._on_delay_expired)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)
        self._icon = QLabel("💡")
        self._text = QLabel("")
        layout.addWidget(self._icon)
        layout.addWidget(self._text, 1)

        self.hide()

    # ---- Public API -------------------------------------------------------

    def attach_to(self, widget: QWidget, shortcut: str, hint: str) -> None:
        """위젯에 hover 힌트 연결. QApplication 이벤트 필터에서 감지.

        Args:
            widget: hover 감지 대상 QWidget.
            shortcut: 표시할 단축키 (예: "⌘K").
            hint: 한 줄 설명 (예: "Open Command Palette").
        """
        widget.setProperty(self._PROPERTY_SHORTCUT, shortcut)
        widget.setProperty(self._PROPERTY_MESSAGE, hint)
        widget.installEventFilter(self)

    def detach(self, widget: QWidget) -> None:
        widget.removeEventFilter(self)
        widget.setProperty(self._PROPERTY_SHORTCUT, None)
        widget.setProperty(self._PROPERTY_MESSAGE, None)

    def set_enabled(self, enabled: bool) -> None:
        """Opt-out 토글. Settings 에서 on/off 가능."""
        self._enabled = enabled
        if not enabled:
            self._delay_timer.stop()
            self._pending_widget = None
            self.hide()

    def show_hint(self, shortcut: str, hint: str) -> None:
        """테스트 / 직접 호출용 — delay 없이 즉시 표시."""
        self._text.setText(f"Press {shortcut} to {hint}")
        self.show()
        self.raise_()

    def hide_hint(self) -> None:
        self._delay_timer.stop()
        self._pending_widget = None
        self.hide()

    @property
    def current_text(self) -> str:
        return self._text.text()

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    # ---- Event filter -----------------------------------------------------

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if not self._enabled:
            return False
        if not isinstance(obj, QWidget):
            return False
        etype = event.type()
        if etype == QEvent.Type.Enter:
            shortcut = obj.property(self._PROPERTY_SHORTCUT)
            hint = obj.property(self._PROPERTY_MESSAGE)
            if shortcut and hint:
                self._pending_widget = obj
                self._delay_timer.start()
        elif etype == QEvent.Type.Leave:
            if self._pending_widget is obj:
                self._delay_timer.stop()
                self._pending_widget = None
            self.hide()
        return False  # do not consume

    def _on_delay_expired(self) -> None:
        widget = self._pending_widget
        if widget is None:
            return
        shortcut = widget.property(self._PROPERTY_SHORTCUT)
        hint = widget.property(self._PROPERTY_MESSAGE)
        if shortcut and hint:
            self.show_hint(str(shortcut), str(hint))


__all__ = ["ShortcutHintBanner"]
