"""
GeoView PySide6 — Visual Effects
==================================
QSS는 box-shadow를 지원하지 않으므로, QGraphicsDropShadowEffect 기반의
깊이감 시스템을 제공한다.

추가 효과:
- HoverLiftEffect: 카드 위젯에 hover 시 그림자 확대 (깊이감 전환)
- PressEffect: 버튼 클릭 시 미세한 opacity dip 피드백
- shake_widget(): 에러 시 위젯 좌우 미세 진동
"""

from PySide6.QtCore import (
    QEvent, QObject, QPropertyAnimation, QEasingCurve,
    QSequentialAnimationGroup, QPoint,
)
from PySide6.QtWidgets import (
    QWidget, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
)
from PySide6.QtGui import QColor


# ════════════════════════════════════════════
# Animation Duration Control
# ════════════════════════════════════════════

_reduce_motion: bool = False


def set_reduce_motion(enabled: bool):
    """Reduce Motion 활성화/비활성화."""
    global _reduce_motion
    _reduce_motion = enabled


def is_reduce_motion() -> bool:
    """현재 Reduce Motion 상태 반환."""
    return _reduce_motion


def anim_duration(base_ms: int) -> int:
    """Reduce Motion이 켜져 있으면 0ms, 아니면 base_ms 반환."""
    return 0 if _reduce_motion else base_ms


# ════════════════════════════════════════════
# Shake Effect
# ════════════════════════════════════════════

def shake_widget(
    widget: QWidget,
    amplitude: int = 3,
    cycles: int = 3,
    duration_ms: int = 200,
) -> None:
    """에러 시 위젯 좌우 미세 진동.

    Args:
        widget: 흔들 대상 위젯.
        amplitude: 좌우 흔들림 폭 (px).
        cycles: 좌→우→좌 반복 횟수.
        duration_ms: 전체 애니메이션 시간 (ms).

    Note:
        Reduce Motion이 켜져 있으면 무시된다.
    """
    actual = anim_duration(duration_ms)
    if actual == 0:
        return

    origin = widget.pos()
    step_ms = max(1, actual // (cycles * 2))

    group = QSequentialAnimationGroup(widget)

    for i in range(cycles):
        # → right
        anim_r = QPropertyAnimation(widget, b"pos")
        anim_r.setDuration(step_ms)
        anim_r.setStartValue(origin)
        anim_r.setEndValue(origin + QPoint(amplitude, 0))
        anim_r.setEasingCurve(QEasingCurve.Type.InOutSine)
        group.addAnimation(anim_r)

        # ← left
        anim_l = QPropertyAnimation(widget, b"pos")
        anim_l.setDuration(step_ms)
        anim_l.setStartValue(origin + QPoint(amplitude, 0))
        anim_l.setEndValue(origin + QPoint(-amplitude, 0))
        anim_l.setEasingCurve(QEasingCurve.Type.InOutSine)
        group.addAnimation(anim_l)

    # 원위치 복귀
    anim_back = QPropertyAnimation(widget, b"pos")
    anim_back.setDuration(step_ms)
    anim_back.setStartValue(origin + QPoint(-amplitude, 0))
    anim_back.setEndValue(origin)
    anim_back.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(anim_back)

    # prevent GC + cleanup
    widget._shake_anim = group
    group.finished.connect(lambda: setattr(widget, '_shake_anim', None))
    group.start()


def apply_shadow(widget: QWidget, level: int = 1,
                 color: str = "#000000") -> QGraphicsDropShadowEffect:
    """
    위젯에 drop shadow 적용.

    Args:
        widget: 대상 위젯
        level: 1=카드(blur 12, offset 2), 2=다이얼로그(blur 20, offset 4), 3=팝오버(blur 30, offset 6)
        color: 그림자 색상

    Returns:
        적용된 QGraphicsDropShadowEffect (나중에 제거 시 사용)

    Note:
        QScrollArea 내부 위젯에는 시각적 아티팩트가 발생할 수 있으므로 주의.
    """
    configs = {
        1: (12, 2, 60),   # blur, offset, alpha
        2: (20, 4, 80),
        3: (30, 6, 100),
    }
    blur, offset, alpha = configs.get(level, configs[1])

    shadow = QGraphicsDropShadowEffect(widget)
    c = QColor(color)
    c.setAlpha(alpha)
    shadow.setColor(c)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset)
    widget.setGraphicsEffect(shadow)
    return shadow


def remove_shadow(widget: QWidget):
    """위젯의 그래픽 이펙트 제거."""
    widget.setGraphicsEffect(None)


# ════════════════════════════════════════════
# HoverLiftEffect
# ════════════════════════════════════════════

class _HoverLiftFilter(QObject):
    """카드 위젯의 hover enter/leave 시 그림자 blur + offset 애니메이션."""

    def __init__(self, widget: QWidget, lift_px: int, parent: QObject | None = None):
        super().__init__(parent or widget)
        self._widget = widget
        self._lift_px = lift_px

        # 기존 그림자가 없으면 level 1 기본 그림자를 먼저 적용
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsDropShadowEffect):
            effect = apply_shadow(widget, level=1)
        self._effect = effect

        # 기본값 저장 (level 1 기준: blur=12, offset=2)
        self._base_blur = effect.blurRadius()
        self._base_offset = effect.offset().y()
        self._hover_blur = self._base_blur + 8  # 12 -> 20
        self._hover_offset = self._base_offset + self._lift_px  # 2 -> 4

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is not self._widget:
            return False

        if event.type() == QEvent.Type.Enter:
            self._animate(self._hover_blur, self._hover_offset)
        elif event.type() == QEvent.Type.Leave:
            self._animate(self._base_blur, self._base_offset)

        return False

    def _animate(self, target_blur: float, target_offset: float):
        # blurRadius 애니메이션
        blur_anim = QPropertyAnimation(self._effect, b"blurRadius", self)
        blur_anim.setDuration(200)
        blur_anim.setEndValue(target_blur)
        blur_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        blur_anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        # yOffset 애니메이션 (QPointF offset 대신 개별 속성 사용 불가이므로
        # 타이머 콜백으로 동기화)
        offset_anim = QPropertyAnimation(self._effect, b"offset", self)
        offset_anim.setDuration(200)
        offset_anim.setEndValue(self._effect.offset().__class__(0, target_offset))
        offset_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        offset_anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


class HoverLiftEffect:
    """카드 위젯에 hover 시 그림자 확대 효과.

    Usage::

        from geoview_pyside6.effects import HoverLiftEffect
        HoverLiftEffect.apply(card_widget)
    """

    @staticmethod
    def apply(widget: QWidget, lift_px: int = 2):
        """위젯에 hover lift 이벤트 필터를 설치.

        Args:
            widget: 대상 위젯 (QGraphicsDropShadowEffect가 없으면 자동 생성)
            lift_px: hover 시 추가 offset 픽셀 (기본 2)
        """
        filt = _HoverLiftFilter(widget, lift_px)
        widget.installEventFilter(filt)
        widget._hover_lift_filter = filt  # prevent GC


# ════════════════════════════════════════════
# PressEffect
# ════════════════════════════════════════════

class _PressFilter(QObject):
    """버튼의 MouseButtonPress 시 opacity dip 애니메이션."""

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            effect = QGraphicsOpacityEffect(obj)
            obj.setGraphicsEffect(effect)

            anim = QPropertyAnimation(effect, b"opacity", obj)
            anim.setDuration(80)
            anim.setStartValue(0.85)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(lambda: obj.setGraphicsEffect(None))
            anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

        return False


class PressEffect:
    """버튼 클릭 시 미세한 opacity dip 피드백.

    Usage::

        from geoview_pyside6.effects import PressEffect
        PressEffect.apply(my_button)
    """

    @staticmethod
    def apply(widget: QWidget):
        """위젯에 press opacity dip 이벤트 필터를 설치.

        Args:
            widget: 대상 위젯 (QPushButton, QToolButton 등)
        """
        filt = _PressFilter(widget)
        widget.installEventFilter(filt)
        widget._press_filter = filt  # prevent GC
