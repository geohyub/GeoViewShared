"""
N5 ReactivePanel (축소판) — 수동 Rerun stale/fresh 전환 (Wave 8)

참조: plans/new_widgets_spec.md §4
      plans/wave8_b3_cptproc_plan.md §3 Day 2~3

v1.0 축소 스펙:
- 자동 재실행 없음
- 파라미터 변경 → sig_stale emit → AnalysisBlock stale 전환
- 사용자가 [Rerun ⟳] 수동 클릭
- v1.1: debounce 500ms 자동 재실행 + dependency graph
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QWidget,
)


class ReactivePanel(QFrame):
    """파라미터 폼 컨테이너 + stale 알림.

    v1.0: 수동 Rerun 전용. 파라미터 변경 시 sig_stale 만 emit.
    """

    sig_stale = Signal()
    sig_params_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ReactivePanel")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._params: dict[str, Any] = {}
        self._fields: dict[str, QLineEdit] = {}

        self._layout = QFormLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)

        self._stale_banner = QLabel("")
        self._stale_banner.setStyleSheet("color: #FBBF24; font-weight: 600;")
        self._stale_banner.setVisible(False)
        self._layout.addRow(self._stale_banner)

    # ---- Public API ----------------------------------------------------------

    def set_params(self, params: dict[str, Any]) -> None:
        """초기 파라미터 설정. 폼 필드 자동 생성."""
        self._params = dict(params)
        # 기존 필드 제거
        for key in list(self._fields.keys()):
            self._fields[key].setParent(None)
        self._fields.clear()
        # 새 필드 생성
        for key, value in params.items():
            field = QLineEdit(str(value))
            field.setObjectName(f"field_{key}")
            field.textChanged.connect(lambda text, k=key: self._on_field_changed(k, text))
            self._fields[key] = field
            self._layout.addRow(QLabel(key), field)
        self._set_stale(False)

    def get_params(self) -> dict[str, Any]:
        """현재 폼 값 반환."""
        result: dict[str, Any] = {}
        for key, field in self._fields.items():
            text = field.text()
            # 숫자 변환 시도
            try:
                result[key] = float(text)
            except ValueError:
                result[key] = text
        return result

    def mark_fresh(self) -> None:
        """Rerun 완료 후 호출 — stale 배너 숨김."""
        self._set_stale(False)

    # ---- Private -------------------------------------------------------------

    def _on_field_changed(self, key: str, text: str) -> None:
        try:
            new_val = float(text)
        except ValueError:
            new_val = text
        old_val = self._params.get(key)
        if new_val != old_val:
            self._params[key] = new_val
            self._set_stale(True)
            self.sig_stale.emit()
            self.sig_params_changed.emit(self.get_params())

    def _set_stale(self, stale: bool) -> None:
        if stale:
            self._stale_banner.setText("⚠ Parameters changed — click Rerun ⟳")
            self._stale_banner.setVisible(True)
        else:
            self._stale_banner.setVisible(False)


__all__ = ["ReactivePanel"]
