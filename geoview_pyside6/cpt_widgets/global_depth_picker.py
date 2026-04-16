"""
N6 GlobalDepthPicker — CPT 3 앱 공통 깊이 범위 선택기 (Wave 6 Day 1)

참조: plans/new_widgets_spec.md §5
Day 1 범위: 2 스핀박스 + preset combo + signal. QRangeSlider 고급 UX 는 Day 4+.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QWidget,
)


@dataclass(frozen=True)
class DepthPreset:
    name: str
    min_m: float
    max_m: float


DEFAULT_PRESETS: tuple[DepthPreset, ...] = (
    DepthPreset("Full depth", 0.0, 100.0),
    DepthPreset("0–5 m", 0.0, 5.0),
    DepthPreset("5–15 m", 5.0, 15.0),
    DepthPreset("Custom", 0.0, 16.0),
)


class GlobalDepthPicker(QWidget):
    """Broadcast 타입 깊이 범위 선택기. 모든 Analysis Block 이 구독."""

    sig_range_changed = Signal(float, float)  # (min_m, max_m)

    def __init__(
        self,
        presets: tuple[DepthPreset, ...] = DEFAULT_PRESETS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._presets: list[DepthPreset] = list(presets)
        self._suppress_signal = False
        self._build_ui()
        self._wire_signals()
        self._install_shortcut()
        self._apply_preset(self._presets[0])

    # ---- UI 구성 -----------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self._label = QLabel("Depth")
        self._label.setProperty("role", "secondary")

        self._min_spin = QDoubleSpinBox()
        self._min_spin.setRange(0.0, 999.9)
        self._min_spin.setSuffix(" m")
        self._min_spin.setDecimals(2)
        self._min_spin.setSingleStep(0.5)

        self._dash = QLabel("–")

        self._max_spin = QDoubleSpinBox()
        self._max_spin.setRange(0.0, 999.9)
        self._max_spin.setSuffix(" m")
        self._max_spin.setDecimals(2)
        self._max_spin.setSingleStep(0.5)

        self._preset_combo = QComboBox()
        for preset in self._presets:
            self._preset_combo.addItem(preset.name)

        layout.addWidget(self._label)
        layout.addWidget(self._min_spin)
        layout.addWidget(self._dash)
        layout.addWidget(self._max_spin)
        layout.addStretch(1)
        layout.addWidget(self._preset_combo)

        self.setFixedHeight(32)

    def _wire_signals(self) -> None:
        self._min_spin.valueChanged.connect(self._on_spin_changed)
        self._max_spin.valueChanged.connect(self._on_spin_changed)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_selected)

    def _install_shortcut(self) -> None:
        shortcut = QShortcut(QKeySequence("D"), self)
        shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        shortcut.activated.connect(self._min_spin.setFocus)

    # ---- 이벤트 핸들러 -----------------------------------------------------

    def _on_spin_changed(self, _value: float) -> None:
        if self._suppress_signal:
            return
        lo, hi = self._current_range()
        if lo > hi:
            self._suppress_signal = True
            self._max_spin.setValue(lo)
            self._suppress_signal = False
            hi = lo
        self.sig_range_changed.emit(lo, hi)

    def _on_preset_selected(self, index: int) -> None:
        if 0 <= index < len(self._presets):
            self._apply_preset(self._presets[index])

    def _apply_preset(self, preset: DepthPreset) -> None:
        self._suppress_signal = True
        self._min_spin.setValue(preset.min_m)
        self._max_spin.setValue(preset.max_m)
        self._suppress_signal = False
        self.sig_range_changed.emit(preset.min_m, preset.max_m)

    def _current_range(self) -> tuple[float, float]:
        return float(self._min_spin.value()), float(self._max_spin.value())

    # ---- Public API --------------------------------------------------------

    def set_range(self, min_m: float, max_m: float) -> None:
        if min_m > max_m:
            raise ValueError(f"min_m ({min_m}) must be <= max_m ({max_m})")
        self._suppress_signal = True
        self._min_spin.setValue(min_m)
        self._max_spin.setValue(max_m)
        self._suppress_signal = False
        self.sig_range_changed.emit(min_m, max_m)

    def get_range(self) -> tuple[float, float]:
        return self._current_range()

    def add_preset(self, name: str, min_m: float, max_m: float) -> None:
        preset = DepthPreset(name, min_m, max_m)
        self._presets.append(preset)
        self._preset_combo.addItem(name)


__all__ = ["GlobalDepthPicker", "DepthPreset", "DEFAULT_PRESETS"]
