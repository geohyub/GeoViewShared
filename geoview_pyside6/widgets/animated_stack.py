"""
GeoView PySide6 -- Animated Stacked Widget
============================================
패널 전환 시 과하지 않은 애니메이션을 제공하는 QStackedWidget.

- fade (기본): 이전 패널 스냅샷이 조용히 사라지는 페이드
- forward/back: 방향 입력은 유지하되 실제 전환은 정적인 fade-through
"""

from PySide6.QtWidgets import (
    QStackedWidget, QGraphicsOpacityEffect, QWidget, QLabel,
)
from PySide6.QtCore import (
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, Qt,
)


class AnimatedStackedWidget(QStackedWidget):
    """방향성 전환을 지원하는 QStackedWidget.

    direction 옵션:
    - "fade" (기본값): 페이드 아웃 -> 교체 -> 페이드 인
    - "forward": 정적인 fade-through 전환
    - "back": 정적인 fade-through 전환
    """

    def __init__(self, duration: int = 200, parent=None):
        super().__init__(parent)
        self._duration = duration
        self._animating = False

    def set_current_with_animation(self, widget: QWidget, direction: str = "fade"):
        """애니메이션과 함께 패널 전환.

        Args:
            widget: 전환할 대상 위젯.
            direction: "fade" | "forward" | "back".
        """
        if self._animating or widget is self.currentWidget():
            return
        if self.currentWidget() is None:
            self.setCurrentWidget(widget)
            return

        from geoview_pyside6.effects import anim_duration
        actual_duration = anim_duration(self._duration)
        if actual_duration == 0:
            # Skip animation entirely
            self.setCurrentWidget(widget)
            return

        if direction in {"forward", "back"} and self.width() > 0:
            self._fade_through_transition(widget, actual_duration)
        else:
            self._fade_transition(widget, actual_duration)

    # ──────────────────────────────────────────
    # Fade cross transition (original behavior)
    # ──────────────────────────────────────────

    def _fade_transition(self, new_widget: QWidget, duration: int):
        """이전 패널 스냅샷만 페이드아웃해 렌더 충돌을 피한다."""
        self._snapshot_transition(new_widget, duration, hold_ratio=0.0)

    # ──────────────────────────────────────────
    # Fade-through transition (forward / back)
    # ──────────────────────────────────────────

    def _fade_through_transition(self, new_widget: QWidget, duration: int):
        """사이드바 전환용 정적인 fade-through.

        새 패널은 제자리에서 서서히 들어오고, 이전 패널만 조용히 걷힌다.
        """
        self._snapshot_transition(new_widget, duration, hold_ratio=0.35)

    def _snapshot_transition(self, new_widget: QWidget, duration: int, hold_ratio: float):
        """Fade an overlay snapshot of the old panel instead of the live widget tree.

        Applying QGraphicsOpacityEffect to full panel trees can trigger QPainter warnings
        when child widgets already use their own effects or custom painting. A lightweight
        snapshot overlay keeps the transition clean without nesting effects on the page.
        """
        self._animating = True
        old_widget = self.currentWidget()
        if old_widget is None:
            self.setCurrentWidget(new_widget)
            self._animating = False
            return

        snapshot = old_widget.grab()
        if snapshot.isNull():
            self.setCurrentWidget(new_widget)
            self._animating = False
            return

        overlay = QLabel(self)
        overlay.setObjectName("stackTransitionOverlay")
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay.setPixmap(snapshot)
        overlay.setGeometry(old_widget.geometry())

        self.setCurrentWidget(new_widget)
        new_widget.show()
        new_widget.raise_()

        overlay.show()
        overlay.raise_()

        opacity = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(opacity)
        opacity.setOpacity(1.0)

        fade = QPropertyAnimation(opacity, b"opacity", self)
        fade.setDuration(duration)
        fade.setStartValue(1.0)
        if hold_ratio > 0:
            fade.setKeyValueAt(max(0.0, min(0.9, hold_ratio)), 1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        self._anim_group = group
        self._transition_overlay = overlay

        def _on_finished():
            self._animating = False
            overlay.setGraphicsEffect(None)
            overlay.hide()
            overlay.deleteLater()
            self._transition_overlay = None

        group.finished.connect(_on_finished)
        group.start()

    def set_current_index_animated(self, index: int, direction: str = "fade"):
        """인덱스로 애니메이션 전환."""
        widget = self.widget(index)
        if widget:
            self.set_current_with_animation(widget, direction=direction)
