"""
GeoView PySide6 — Animated Stacked Widget
============================================
패널 전환 시 페이드 크로스 애니메이션을 제공하는 QStackedWidget.
"""

from PySide6.QtWidgets import QStackedWidget, QGraphicsOpacityEffect, QWidget
from PySide6.QtCore import (
    QPropertyAnimation, QSequentialAnimationGroup, QEasingCurve,
    QParallelAnimationGroup, Qt, Slot,
)


class AnimatedStackedWidget(QStackedWidget):
    """페이드 크로스 전환을 지원하는 QStackedWidget."""

    def __init__(self, duration: int = 200, parent=None):
        super().__init__(parent)
        self._duration = duration
        self._animating = False

    def set_current_with_animation(self, widget: QWidget):
        """페이드 아웃 → 교체 → 페이드 인 전환."""
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

        self._animating = True
        old_widget = self.currentWidget()
        new_widget = widget

        # Opacity effects
        old_effect = QGraphicsOpacityEffect(old_widget)
        old_widget.setGraphicsEffect(old_effect)
        old_effect.setOpacity(1.0)

        new_effect = QGraphicsOpacityEffect(new_widget)
        new_widget.setGraphicsEffect(new_effect)
        new_effect.setOpacity(0.0)

        # Fade out old
        fade_out = QPropertyAnimation(old_effect, b"opacity")
        fade_out.setDuration(self._duration // 2)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)

        # Fade in new
        fade_in = QPropertyAnimation(new_effect, b"opacity")
        fade_in.setDuration(self._duration // 2)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Sequence: fade out -> switch -> fade in
        self._anim_group = QSequentialAnimationGroup(self)

        fade_out.finished.connect(lambda: self.setCurrentWidget(new_widget))
        self._anim_group.addAnimation(fade_out)
        self._anim_group.addAnimation(fade_in)

        def _on_finished():
            self._animating = False
            # Clean up effects to avoid interference
            old_widget.setGraphicsEffect(None)
            new_widget.setGraphicsEffect(None)

        self._anim_group.finished.connect(_on_finished)
        self._anim_group.start()

    def set_current_index_animated(self, index: int):
        """인덱스로 애니메이션 전환."""
        widget = self.widget(index)
        if widget:
            self.set_current_with_animation(widget)
