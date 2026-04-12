"""
GeoView PySide6 -- Animated Stacked Widget
============================================
패널 전환 시 다양한 애니메이션을 제공하는 QStackedWidget.

- fade (기본): 페이드 크로스 전환
- forward: 새 패널이 우측에서 슬라이드 인
- back: 새 패널이 좌측에서 슬라이드 인
"""

from PySide6.QtWidgets import QStackedWidget, QGraphicsOpacityEffect, QWidget
from PySide6.QtCore import (
    QPropertyAnimation, QSequentialAnimationGroup, QEasingCurve,
    QParallelAnimationGroup, Qt, Slot, QPoint,
)


class AnimatedStackedWidget(QStackedWidget):
    """방향성 전환을 지원하는 QStackedWidget.

    direction 옵션:
    - "fade" (기본값): 페이드 아웃 -> 교체 -> 페이드 인
    - "forward": 새 패널이 오른쪽에서 슬라이드 인
    - "back": 새 패널이 왼쪽에서 슬라이드 인
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
            self._slide_transition(widget, direction, actual_duration)
        else:
            self._fade_transition(widget, actual_duration)

    # ──────────────────────────────────────────
    # Fade cross transition (original behavior)
    # ──────────────────────────────────────────

    def _fade_transition(self, new_widget: QWidget, duration: int):
        """페이드 아웃 -> 교체 -> 페이드 인 전환."""
        self._animating = True
        old_widget = self.currentWidget()

        # Opacity effects
        old_effect = QGraphicsOpacityEffect(old_widget)
        old_widget.setGraphicsEffect(old_effect)
        old_effect.setOpacity(1.0)

        new_effect = QGraphicsOpacityEffect(new_widget)
        new_widget.setGraphicsEffect(new_effect)
        new_effect.setOpacity(0.0)

        # Fade out old
        fade_out = QPropertyAnimation(old_effect, b"opacity")
        fade_out.setDuration(duration // 2)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)

        # Fade in new
        fade_in = QPropertyAnimation(new_effect, b"opacity")
        fade_in.setDuration(duration // 2)
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

    # ──────────────────────────────────────────
    # Slide transition (forward / back)
    # ──────────────────────────────────────────

    def _slide_transition(self, new_widget: QWidget, direction: str, duration: int):
        """부드러운 슬라이드 + 페이드 전환.

        forward: 새 패널이 오른쪽에서 살짝 슬라이드 인 (15% offset).
        back:    새 패널이 왼쪽에서 살짝 슬라이드 인.
        이전 패널은 제자리에서 페이드 아웃만.
        """
        self._animating = True
        old_widget = self.currentWidget()
        w = self.width()

        # 짧은 오프셋 (15%) — 과하지 않게
        offset = int(w * 0.15)
        if direction == "forward":
            new_start_x = offset
            old_end_x = 0  # 이전 패널은 이동 안 함
        else:  # back
            new_start_x = -offset
            old_end_x = 0

        # 새 위젯을 시작 위치에 배치하고 보이게
        new_widget.show()
        new_widget.raise_()
        origin_pos = old_widget.pos()
        new_widget.move(origin_pos.x() + new_start_x, origin_pos.y())

        # 이전 위젯을 현재 위젯으로 유지하면서 슬라이드 시작
        # (setCurrentWidget은 완료 후 호출)

        # Opacity effects for smooth entrance
        old_opacity = QGraphicsOpacityEffect(old_widget)
        old_widget.setGraphicsEffect(old_opacity)
        old_opacity.setOpacity(1.0)

        new_opacity = QGraphicsOpacityEffect(new_widget)
        new_widget.setGraphicsEffect(new_opacity)
        new_opacity.setOpacity(0.0)

        # -- Parallel animation group --
        group = QParallelAnimationGroup(self)

        # Old widget fades out (no slide, just disappear)
        old_fade = QPropertyAnimation(old_opacity, b"opacity")
        old_fade.setDuration(duration)
        old_fade.setStartValue(1.0)
        old_fade.setEndValue(0.0)
        old_fade.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(old_fade)

        # New widget slides in
        new_slide = QPropertyAnimation(new_widget, b"pos")
        new_slide.setDuration(duration)
        new_slide.setStartValue(QPoint(origin_pos.x() + new_start_x, origin_pos.y()))
        new_slide.setEndValue(origin_pos)
        new_slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(new_slide)

        # New widget fades in
        new_fade = QPropertyAnimation(new_opacity, b"opacity")
        new_fade.setDuration(duration)
        new_fade.setStartValue(0.0)
        new_fade.setEndValue(1.0)
        new_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        group.addAnimation(new_fade)

        self._anim_group = group

        def _on_finished():
            self._animating = False
            # Switch stacked widget current
            self.setCurrentWidget(new_widget)
            # Reset positions and effects
            old_widget.move(origin_pos)
            new_widget.move(origin_pos)
            old_widget.setGraphicsEffect(None)
            new_widget.setGraphicsEffect(None)

        group.finished.connect(_on_finished)
        group.start()

    def set_current_index_animated(self, index: int, direction: str = "fade"):
        """인덱스로 애니메이션 전환."""
        widget = self.widget(index)
        if widget:
            self.set_current_with_animation(widget, direction=direction)
