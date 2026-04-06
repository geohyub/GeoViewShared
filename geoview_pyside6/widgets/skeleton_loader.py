"""
GeoView PySide6 — Skeleton Loaders
====================================
데이터 로딩 중 표시되는 스켈레톤 플레이스홀더 위젯들.
좌->우 시머(shimmer) 하이라이트 애니메이션 포함.

Usage::

    # 단일 사각형
    rect = SkeletonRect(height=20)

    # 여러 줄 텍스트
    text = SkeletonText(lines=4)

    # KPI 카드 모양
    kpi = SkeletonKPICard()

    # 테이블 행
    table = SkeletonTableRows(rows=8, columns=5)

    # 로딩 완료 후 실제 위젯으로 교체
    stack = QStackedWidget()
    stack.addWidget(kpi_skeleton)
    stack.addWidget(real_kpi)
    stack.setCurrentIndex(1)  # 로딩 완료 시
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from geoview_pyside6.constants import Radius, Space
from geoview_pyside6.theme_aware import c

# ────────────────────────────────────────────
# Module-level singleton timer
# ────────────────────────────────────────────
# 모든 SkeletonRect가 동일한 타이머를 공유하여 시머가 동기화된다.

_shimmer_timer: Optional[QTimer] = None
_shimmer_offset: float = -0.4
_shimmer_listeners: list = []  # callable list


def _ensure_timer() -> QTimer:
    """싱글톤 QTimer를 생성/반환한다."""
    global _shimmer_timer
    if _shimmer_timer is None:
        _shimmer_timer = QTimer()
        _shimmer_timer.setInterval(30)  # ~33 fps
        _shimmer_timer.timeout.connect(_advance_shimmer)
        _shimmer_timer.start()
    return _shimmer_timer


def _advance_shimmer():
    """오프셋을 전진시키고 모든 리스너에 repaint를 요청한다."""
    global _shimmer_offset
    # 30ms * ~60 steps = ~1.8s, 범위 1.8 => step ~0.03
    _shimmer_offset += 0.03
    if _shimmer_offset > 1.4:
        _shimmer_offset = -0.4
    for listener in _shimmer_listeners:
        try:
            listener()
        except RuntimeError:
            pass  # 위젯이 이미 삭제된 경우 무시


# ────────────────────────────────────────────
# Shimmer Mixin
# ────────────────────────────────────────────

class _ShimmerMixin:
    """
    시머 애니메이션 공통 로직.

    QFrame 서브클래스에서 mixin으로 사용한다.
    ``paintEvent`` 에서 QPainter로 하이라이트 그래디언트를 그린다.

    색상 체계:
        배경:   c().NAVY
        시머:   c().SLATE -> c().SURFACE -> c().SLATE
        하이라이트 폭: 위젯 너비의 40%
        주기: ~1.5초 (좌->우)
    """

    @property
    def _bg_color(self):
        return QColor(c().NAVY)

    @property
    def _shimmer_base(self):
        return QColor(c().SLATE)

    @property
    def _shimmer_peak(self):
        return QColor(c().SURFACE)

    def _init_shimmer(self):
        """mixin 초기화. __init__ 끝에서 호출해야 한다."""
        _ensure_timer()
        _shimmer_listeners.append(self.update)

    def _cleanup_shimmer(self):
        """리스너 제거. 위젯 파괴 시 호출."""
        try:
            _shimmer_listeners.remove(self.update)
        except ValueError:
            pass

    def _paint_shimmer(self, painter: QPainter):
        """현재 오프셋에 따른 시머 그래디언트를 그린다."""
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        # 배경
        painter.fillRect(0, 0, w, h, self._bg_color)

        # 시머 하이라이트
        highlight_w = w * 0.4
        center_x = _shimmer_offset * w

        grad = QLinearGradient(center_x - highlight_w / 2, 0,
                               center_x + highlight_w / 2, 0)

        transparent = QColor(self._shimmer_base)
        transparent.setAlpha(0)

        peak = QColor(self._shimmer_peak)
        peak.setAlpha(128)  # 50% alpha

        grad.setColorAt(0.0, transparent)
        grad.setColorAt(0.5, peak)
        grad.setColorAt(1.0, transparent)

        painter.fillRect(0, 0, w, h, grad)


# ────────────────────────────────────────────
# SkeletonRect
# ────────────────────────────────────────────

class SkeletonRect(_ShimmerMixin, QFrame):
    """
    사각형 스켈레톤 플레이스홀더.

    Args:
        width:   고정 폭 (px). None이면 부모 폭에 맞춤.
        height:  고정 높이 (px). 기본 20.
        rounded: True이면 Radius.SM 적용.
        parent:  부모 위젯.
    """

    def __init__(
        self,
        width: Optional[int] = None,
        height: int = 20,
        rounded: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._rounded = rounded

        self.setFixedHeight(height)
        if width is not None:
            self.setFixedWidth(width)
        else:
            self.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Fixed)

        self._init_shimmer()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._rounded:
            r = Radius.SM
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self._bg_color)
            painter.drawRoundedRect(self.rect(), r, r)
            # clip 후 시머
            path = painter.clipPath()
            if path.isEmpty():
                from PySide6.QtGui import QPainterPath
                path = QPainterPath()
                path.addRoundedRect(0, 0, self.width(), self.height(),
                                    float(r), float(r))
                painter.setClipPath(path)
            self._paint_shimmer(painter)
        else:
            self._paint_shimmer(painter)

        painter.end()

    def hideEvent(self, event):
        self._cleanup_shimmer()
        super().hideEvent(event)

    def showEvent(self, event):
        # 다시 보이면 리스너 재등록
        if self.update not in _shimmer_listeners:
            _shimmer_listeners.append(self.update)
        super().showEvent(event)


# ────────────────────────────────────────────
# SkeletonText
# ────────────────────────────────────────────

class SkeletonText(QFrame):
    """
    여러 줄 텍스트 스켈레톤.

    Args:
        lines:       줄 수. 기본 3.
        line_height: 각 줄 높이 (px). 기본 14.
        spacing:     줄 간격 (px). 기본 8.
        parent:      부모 위젯.
    """

    def __init__(
        self,
        lines: int = 3,
        line_height: int = 14,
        spacing: int = 8,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing)

        for i in range(lines):
            rect = SkeletonRect(height=line_height, parent=self)
            # 마지막 줄은 60% 폭
            if i == lines - 1 and lines > 1:
                rect.setSizePolicy(QSizePolicy.Policy.Preferred,
                                   QSizePolicy.Policy.Fixed)
                rect.setMaximumWidth(16777215)  # reset
                # 60% 비율은 resizeEvent에서 적용
                rect.setProperty("_last_line", True)
            layout.addWidget(rect)

        self._lines_widgets = [
            layout.itemAt(i).widget() for i in range(layout.count())
        ]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        for rect in self._lines_widgets:
            if rect.property("_last_line"):
                rect.setFixedWidth(max(int(w * 0.6), 40))


# ────────────────────────────────────────────
# SkeletonKPICard
# ────────────────────────────────────────────

class SkeletonKPICard(QFrame):
    """
    KPICard 모양 스켈레톤.

    구조:
        가로 배치: [44x44 원형 rect] + [세로: 26px value rect + 12px label rect]
        gvCard 스타일 (c().NAVY bg, c().BORDER border, Radius.SM)
        고정 높이 72px
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("gvCard")
        self.setFixedHeight(72)
        self.setStyleSheet(
            f"#gvCard {{"
            f"  background: {c().NAVY};"
            f"  border: 1px solid {c().BORDER};"
            f"  border-radius: {Radius.SM}px;"
            f"}}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Space.BASE, Space.MD, Space.BASE, Space.MD)
        layout.setSpacing(Space.SM)

        # 아이콘 영역 (44x44, 둥근 사각형)
        icon_rect = SkeletonRect(width=44, height=44, rounded=True, parent=self)
        layout.addWidget(icon_rect)

        # 텍스트 영역
        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        value_rect = SkeletonRect(width=80, height=26, parent=self)
        label_rect = SkeletonRect(width=56, height=12, parent=self)

        text_layout.addWidget(value_rect)
        text_layout.addWidget(label_rect)

        layout.addLayout(text_layout)
        layout.addStretch()


# ────────────────────────────────────────────
# SkeletonTableRows
# ────────────────────────────────────────────

class SkeletonTableRows(QFrame):
    """
    테이블 행 스켈레톤.

    Args:
        rows:    행 수. 기본 5.
        columns: 열 수. 기본 4.
        parent:  부모 위젯.

    각 셀: SkeletonRect(height=14)
    행 간격: 36px (GVTableView 행 높이와 동일)
    열 간격: Space.SM (8px)
    """

    def __init__(
        self,
        rows: int = 5,
        columns: int = 4,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(Space.SM)
        grid.setVerticalSpacing(0)

        row_height = 36  # GVTableView 기본 행 높이

        for r in range(rows):
            for c in range(columns):
                cell = SkeletonRect(height=14, parent=self)
                # 셀을 행 높이 중앙에 배치하기 위한 래퍼
                wrapper = QFrame(self)
                wrapper.setStyleSheet("background: transparent; border: none;")
                wrapper.setFixedHeight(row_height)
                wrapper_layout = QVBoxLayout(wrapper)
                wrapper_layout.setContentsMargins(0, 0, 0, 0)
                wrapper_layout.addStretch()
                wrapper_layout.addWidget(cell)
                wrapper_layout.addStretch()

                grid.addWidget(wrapper, r, c)


__all__ = [
    "SkeletonRect",
    "SkeletonText",
    "SkeletonKPICard",
    "SkeletonTableRows",
]
